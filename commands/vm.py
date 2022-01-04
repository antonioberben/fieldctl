import subprocess
import click
import logging
import yaml
import json
import shutil
import helpers
import click_log
import os
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
click_log.basic_config(logger)


@click.group()
@click.pass_obj
def vm(ctx):
    """Configure a vm with Lima (https://github.com/lima-vm/lima)
    
    TIPS:
    
    - Images will be persisted so that you can freely destroy the VM and recreating without loosing the images which were already pulled
    
    - The name of the VM is local-k3s
    """
    returncode, _ = helpers.run_command(f"which limactl", subprocess.PIPE)
    if returncode != 0:
        logger.error(f"You need to install limactl (https://github.com/lima-vm/lima)")
        raise click.Abort()
    pass


@vm.command("version", help="Show the Lima version")
@click.pass_obj
def version(ctx):
    helpers.run_command(f"limactl --version")
    return


@vm.command("ls", help=f"List all Lima VMs and show status")
@click.pass_obj
def list(ctx):
    helpers.run_command(f"limactl ls")
    return


@vm.command("get-config", help="Get the default config for the Lima VM")
@click.pass_obj
def get_config(ctx):
    with open(ctx["LIMA_TEMPLATE"]) as file:
        print(
            yaml.dump(yaml.load(file, Loader=yaml.FullLoader), default_flow_style=False)
        )
    return


@vm.command("stop", help="Stop the Lima VM")
@click.pass_obj
def stop(ctx):
    helpers.run_command(f"limactl stop {ctx['VM_NAME']}")
    return


@vm.command("start", help="Start teh Lima VM")
@click.pass_obj
def start(ctx):
    _, out = helpers.run_command(f"limactl ls --json", subprocess.PIPE)
    out = ",".join(out.strip().split("\n"))
    out = "[" + out + "]"
    vms = json.loads(out)
    if not len([i for i in vms if i["name"] == ctx["VM_NAME"]]):
        logger.error(f"{ctx['VM_NAME']} does not exist yet. irt, run `create`")
        raise click.Abort()
    helpers.run_command(f"limactl start --tty=false {ctx['VM_NAME']}")
    return


@vm.command("create", help="Create the Lima VM")
@click.option("--config", "-c", help="Lima config file. Otherwise, it will use default")
@click.option("--cpus", default=4, help="Lima CPUs")
@click.option("--disk", default="50", help="Lima Disk space in Gi. Only the number 50 means 50GiB")
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
def create(ctx, config, cpus, disk, connect, kubeconfig):
    logger.info(f"Persisted data will be created in {ctx['PERSISTED_FOLDER']}")
    shutil.copytree(
        f"{ctx['PROVISION_FOLDER']}", ctx["PERSISTED_FOLDER"], dirs_exist_ok=True
    )
    filename = f"/tmp/{ctx['VM_NAME']}.yaml"
    if config is None:
        logger.info(
            "No config supplied. Using default configuration. See `get-config` to check the configuration"
        )
        shutil.copy(ctx["LIMA_TEMPLATE"], filename)
    else:
        shutil.copy(config, filename)
    helpers.update_cpus_and_disk(ctx, filename, cpus, disk)
    helpers.add_home_persisted_folder(ctx, filename)
    helpers.add_forwarded_port(ctx, filename)
    helpers.run_command(f"limactl validate {filename}")
    logger.info(f"Create the Lima VM with name: {ctx['VM_NAME']}")
    helpers.run_command(f"limactl start --tty=false {filename}")
    logger.info(
        f"Install cache registries since it cannot be done in provision scripts"
    )
    helpers.run_command(
        f"limactl shell {ctx['VM_NAME']} sh -c 'cd $FIELDCTL_HOME; ./deploy-caches.sh'"
    )
    if connect:
        helpers.connect_to_cluster(kubeconfig)
    return


@vm.command("rm", help="Remove the the Lima VM")
@click.pass_obj
def remove(ctx):
    helpers.run_command(f"limactl rm {ctx['VM_NAME']} -f")
    return


@vm.command(
    "show-ssh",
    help="Show the ssh command to access the Lima VM. You can run `eval(fieldctl vm show-ssh)` to access directly",
)
@click.pass_obj
def show_ssh(ctx):
    logger.info(f"TIP: To access directly run:\n")
    logger.info(f"    eval(fieldctl vm show-ssh)\n\n\n")
    helpers.run_command(f"limactl show-ssh {ctx['VM_NAME']}")
    return


@vm.command("connect", help="Get k3s kubeconfig file to connect to the cluster")
@click.option(
    "--kubeconfig",
    "-kc",
    help="Kubeconfig file to update. It will also check $KUBECONFIG or default to `~/.kube/config`",
)
@click.pass_obj
def connect(ctx, kubeconfig):
    helpers.connect_to_cluster(ctx, kubeconfig)
    return

