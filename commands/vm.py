import logging
import shutil

import click
import click_log
import helpers

logger = logging.getLogger('root')


@click.group()
@click.pass_obj
def vm(ctx):
    """Operate a VM containing a main cluster
    
    To know more about Lima VM: https://github.com/lima-vm/lima
    
    TIPS:
    
    - Images will be persisted so that you can freely destroy the VM and recreating without loosing the images which were already pulled
    
    - Mind the resources (CPUs, disk and memory) for the VM when creating many virtual clusters
    """
    returncode, _ = helpers.new_run_command(f"which limactl")
    if returncode != 0:
        logger.error(f"You need to install limactl (https://github.com/lima-vm/lima)")
        raise click.Abort()
    pass


@vm.command("version", help="Show the Lima version")
@click.pass_obj
def version(ctx):
    helpers.new_run_command(f"limactl --version", show_output=True)
    return


@vm.command("stop", help="Stop the Lima VM")
@click.pass_obj
def stop(ctx):
    if not helpers.vm_exist(ctx["VM_NAME"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    returncode, out = helpers.new_run_command(f"limactl stop {ctx['VM_NAME']}", show_output=True)
    if returncode != 0:
        logging.error(out)
        raise click.Abort()
    logging.info("VM Stopped")
    return


@vm.command("start", help="Start teh Lima VM")
@click.pass_obj
def start(ctx):
    if not helpers.vm_exist(ctx["VM_NAME"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    returncode, out = helpers.new_run_command(f"limactl start --tty=false {ctx['VM_NAME']}", show_output=True)
    if returncode != 0:
        logging.error("Error creating the VM")
        logging.error(out)
        raise click.Abort()
    logging.info("VM started. To merge the kubeconfig run:\n\n  fieldctl vm connect")




@vm.command("create", help="Create the Lima VM")
@click.option("--cpus", default=4, help="Lima CPUs")
@click.option(
    "--disk",
    default="50",
    help="Lima Disk space in GiB. Expects a number. i.e. 50 means 50GiB",
)
@click.option(
    "--memory",
    default=8,
    help="Memory allocated for the VM in GiB. Expects a number. i.e. 8 means 8GiB",
)
@click.option(
    "--connect",
    "-conn",
    is_flag=True,
    default=False,
    help="Merge current kubeconfig with the generated in Lima VM",
)
@click.option(
    "--kubeconfig",
    "-kc",
    help="Kubeconfig file to update. It will also check $KUBECONFIG or default to `~/.kube/config`",
)
@click_log.simple_verbosity_option(logger)
@click.pass_obj
def create(ctx, cpus, disk, memory, connect, kubeconfig):
    logger.info(f"Using following values:\n\ncpus: {cpus}\ndisk: {disk}GiB\nmemory: {memory}")
    logger.info(f"Persisted data will be created in {ctx['PERSISTED_FOLDER']}")
    helpers.copy_persisted_folder(ctx['PROVISION_FOLDER'], ctx["PERSISTED_FOLDER"])
    filename = f"/tmp/{ctx['VM_NAME']}.yaml"
    shutil.copy(ctx["LIMA_TEMPLATE"], filename)
    helpers.update_allocated_resources(ctx, filename, cpus, disk, memory)
    helpers.add_home_persisted_folder(ctx, filename)
    helpers.add_forwarded_port(ctx, filename)
    returncode, out = helpers.new_run_command(f"limactl validate {filename}")
    if returncode != 0:
        logging.error("Error validating the VM")
        logging.error(out)
        raise click.Abort()
    logger.info(f"Create the Lima VM with name: {ctx['VM_NAME']}")
    helpers.new_run_command(f"limactl start --tty=false {filename}", show_output=True)
    logger.info(
        f"Install cache registries. This happens here since it cannot be done in provision scripts"
    )
    returncode, out = helpers.new_run_command(
        f"limactl shell {ctx['VM_NAME']} sh -c 'cd $FIELDCTL_HOME; ./deploy-caches.sh'"
    )
    if returncode != 0:
        logging.error("Error creating registries")
        logging.error(out)
        raise click.Abort()
    if connect:
        logging.info("Download kubeconfig from VM and mergng into the current one")
        kubeconfig_path = helpers.get_current_kubeconfig_path(ctx, kubeconfig)
        returncode, out = helpers.connect_to_main_cluster(ctx, kubeconfig_path)
        if returncode != 0:
            logging.error(out)
            raise click.Abort()
    logging.info("VM created. Now run:\n\n  fieldctl vm connect\t\tto connect to the main cluster\n\n  fieldctl cluster create -n <name>\t\tto create a virtual cluster")
    return




@vm.command("rm", help="Remove the the Lima VM")
@click.pass_obj
def remove(ctx):
    if not helpers.vm_exist(ctx["VM_NAME"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    returncode, out = helpers.new_run_command(f"limactl rm {ctx['VM_NAME']} -f")
    if returncode != 0:
        logging.error("Error deleting registries")
        logging.error(out)
        raise click.Abort()
    logging.info("VM deleted")
    return


@vm.command(
    "show-ssh",
    help="Show the ssh command to access the Lima VM. You can run `eval(fieldctl vm show-ssh)` to access directly",
)
@click.pass_obj
def show_ssh(ctx):
    logger.info(f"TIP: To access directly run:\n")
    logger.info(f"    eval(fieldctl vm show-ssh)\n\n\n")
    returncode, out = helpers.new_run_command(f"limactl show-ssh {ctx['VM_NAME']}")
    if returncode != 0:
        logging.error(out)
        raise click.Abort()
    logging.info(out)
    return


@vm.command("connect", help="Get k3s kubeconfig file to connect to the cluster")
@click.option(
    "--kubeconfig",
    "-kc",
    help="Kubeconfig file to update. It will also check $KUBECONFIG or default to `~/.kube/config`",
)
@click.pass_obj
def connect(ctx, kubeconfig):
    kubeconfig_path = helpers.get_current_kubeconfig_path(ctx, kubeconfig)
    if not helpers.vm_exist(ctx["VM_NAME"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    helpers.connect_to_main_cluster(ctx, kubeconfig_path)
    logging.info("Connect to main cluster in VM. Run:\n\n kubectl config get-contexts\t\tto se the new context")

