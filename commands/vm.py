import logging
import shutil

import click
import helpers.cluster_helper as cluster
import helpers.vm_helper as vmh
import helpers.shell_helper as sh

logger = logging.getLogger('root')


@click.group('vm')
@click.pass_obj
def vm(ctx):
    """Operate a Lima VM with a k3s cluster (main cluster)
    
    To know more about Lima VM: https://github.com/lima-vm/lima
    
    TIPS:
    
    - Images will be persisted so that you can freely destroy the VM and recreating without loosing the images which were already pulled
    
    - Mind the resources (CPUs, disk and memory) for the VM when creating many virtual clusters
    """
    # Verify that limactl is installed in the host
    returncode, _ = sh.run_command(f"which limactl")
    if returncode != 0:
        logger.error(f"You need to install limactl (https://github.com/lima-vm/lima)")
        raise click.Abort()


@vm.command("version", help="Show the Lima version is installed in you host")
@click.pass_obj
def version(ctx):
    # Returns limactl version
    sh.run_command(f"limactl --version", show_output=True)
    return


@vm.command("stop", help="Stop the Lima VM")
@click.pass_obj
def stop(ctx):
    if not vmh.vm_exist(ctx["MAIN_CONTEXT"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    returncode, out = sh.run_command(f"limactl stop {ctx['MAIN_CONTEXT']}", show_output=True)
    if returncode != 0:
        logging.error(out)
        raise click.Abort()
    logging.info("VM Stopped")
    return


@vm.command("start", help="Start teh Lima VM")
@click.pass_obj
def start(ctx):
    # Verify VM exist
    if not vmh.vm_exist(ctx["MAIN_CONTEXT"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    
    # Starts VM
    returncode, out = sh.run_command(f"limactl start --tty=false {ctx['MAIN_CONTEXT']}", show_output=True)
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
    help="Kubeconfig file to update",
    show_default="$KUBECONFIG or `~/.kube/config`"
)
@click.pass_obj
def create(ctx, cpus, disk, memory, connect, kubeconfig):
    logger.info(f"Using following values:\ncpus: {cpus}\ndisk: {disk}GiB\nmemory: {memory}")
    logger.info(f"Persisted data will be created in {ctx['PERSISTED_FOLDER']}")
    # Copy the provision folder into the fodler which will be persisted into the VM. This is `~/.field`
    vmh.copy_persisted_folder(ctx['PROVISION_FOLDER'], ctx["PERSISTED_FOLDER"])
    filename = f"/tmp/{ctx['MAIN_CONTEXT']}.yaml"
    
    # Copy the template to a temporary location and update its values to include port, resources and persisted folder
    shutil.copy(ctx["LIMA_TEMPLATE"], filename)
    vmh.update_allocated_resources(ctx, filename, cpus, disk, memory)
    vmh.add_home_persisted_folder(ctx, filename)
    vmh.add_forwarded_port(ctx, filename)
    
    # Validate the configuration works
    returncode, out = sh.run_command(f"limactl validate {filename} --debug")
    if returncode != 0:
        logging.error("Error validating the VM")
        logging.error(out)
        raise click.Abort()
    
    # Create VM
    logger.info(f"Create the Lima VM with name: {ctx['MAIN_CONTEXT']}")
    returncode, _ = sh.run_command(f"limactl start --tty=false {filename}", show_output=True)
    if returncode != 0:
        logging.error("Error creating the machine. Try again:\n\n\tfieldctl vm rm\t\t\t-- Remove the created files\n\tfieldctl vm create\t\t-- Create again")
        raise click.Abort()
    
    logger.info(
        f"Install cache registries. This happens here since it cannot be done in provision scripts"
    )
    # Install docker registry caches (grc, quay, k8s, docker). The context of this fodler is persisted in `~\fieldctl`
    returncode, out = sh.run_command(
        f"limactl shell --workdir='/' {ctx['MAIN_CONTEXT']} sh -c 'cd $FIELDCTL_HOME; ./deploy-caches.sh'"
    )
    if returncode != 0:
        logging.error("Error creating registries")
        logging.error(out)
        raise click.Abort()
    
    # Connect to the k3s (main cluster) provisioned in the VM. 
    # The kubeconfig file will be updated with te new details for the main cluster context
    if connect:
        logging.info("Download kubeconfig from VM and mergng into the current one")
        kubeconfig_path = cluster.get_current_kubeconfig_path(ctx, kubeconfig)
        returncode, out = cluster.connect_to_main_cluster(ctx, kubeconfig_path)
        if returncode != 0:
            logging.error(out)
            raise click.Abort()
    logging.info("VM created. Now run:\n\n  fieldctl vm connect\t\t\t\tto connect to the main cluster\n\n  fieldctl virtual create -n <name>\t\tto create a virtual cluster")
    return




@vm.command("rm", help="Remove the the Lima VM")
@click.option(
    "--kubeconfig",
    help="Kubeconfig file to update",
    show_default="$KUBECONFIG or `~/.kube/config`"
)
@click.pass_obj
def remove(ctx, kubeconfig):
    # Verify VM exist
    if not vmh.vm_exist(ctx["MAIN_CONTEXT"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    
    # Remove VM
    returncode, out = sh.run_command(f"limactl rm {ctx['MAIN_CONTEXT']} -f")
    if returncode != 0:
        logging.error("Error deleting registries")
        logging.error(out)
        raise click.Abort()
    kubeconfig = cluster.get_current_kubeconfig_path(ctx, kubeconfig)
    cluster.remove_context_from_kubeconfig(kubeconfig, {ctx['MAIN_CONTEXT']})
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
    # Shows the command to connect to the VM
    returncode, out = sh.run_command(f"limactl show-ssh {ctx['MAIN_CONTEXT']}")
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
    # Connect to the k3s (main cluster) deployed in the VM
    kubeconfig_path = cluster.get_current_kubeconfig_path(ctx, kubeconfig)
    if not vmh.vm_exist(ctx["MAIN_CONTEXT"]):
        logging.error("VM does not exist. Create it")
        raise click.Abort()
    cluster.connect_to_main_cluster(ctx, kubeconfig_path)
    logging.info("Connect to main cluster. Run:\n\n kubectl config get-contexts\t\t-- to see the new context")