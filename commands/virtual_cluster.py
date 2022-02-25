import logging

import click
import helpers.cluster_helper as cluster
import helpers.vm_helper as vm
import helpers.shell_helper as sh
import yaml

logger = logging.getLogger('root')

TMP_VALUES_FILE = "/tmp/vcluster-values.yaml"
CURRENT_CONTEXT="current-context"

def set_context(ctx, param, value):
    """Method to define which is the context to be used: user defined, $KBECONFIG or `~/.kube/config`
    """
    if value == CURRENT_CONTEXT:
        logging.info(f"You are not using the VM as main cluster. Instead, you are using the active CURRENT CONTEXT. This might not be what you want")
        ctx.obj["MAIN_CONTEXT"] = value
        return
    if value:
        logging.info(f"You are not using the VM as main cluster. Instead, you are using context: {value}")
        ctx.obj["MAIN_CONTEXT"] = value
    logging.info(f"You are using the VM as main cluster with context: {ctx.obj['MAIN_CONTEXT']}")

# Option re-used by multiple commands
_common_options = [
    click.option("--main-context", '-ctx', is_flag=False, flag_value=CURRENT_CONTEXT,
    callback=set_context,
    help="Use TEXT context as main cluster instead of the one in the VM. This is useful when you do not want Lima VM",
    show_default="current context")
]


def add_options(options):
    """Add the option which will be used by multiple commands
    """
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options


@click.group('virtual')
@click.pass_obj
def virtual_cluster(ctx):
    """Operate ephemeral virtual clusters.
    
    To know more about vcluster: https://www.vcluster.com/
    
    TIPS:
    
    - You do not need a Lima VM. With the attribute -ctx you can specify which is the context to the main cluster
    
    - Mind the resources (CPUs, disk and memory) for the VM when creating many virtual clusters
    """
    # Verify vcluster is installed
    returncode, _ = sh.run_command(f"which vcluster")
    if returncode != 0:
        logger.error(
            f"You need to install vcluster (https://www.vcluster.com/docs/getting-started/setup#download-vcluster-cli)"
        )
        raise click.Abort()
    # Verify kubectl is installed
    returncode, _ = sh.run_command("which kubectl")
    if returncode != 0:
        logger.error(
            f"You need to install kubectl (https://kubernetes.io/docs/tasks/tools/)"
        )
        raise click.Abort()
    pass


@virtual_cluster.command("list", help=f"List all vclusters in the main cluster")
@add_options(_common_options)
@click.pass_obj
def list(ctx, main_context):
    """This command wraps vclusters' one.
    
    It shows the vcluster which are installed in the main cluster.
    """
    sh.run_command(f"vcluster --context {ctx['MAIN_CONTEXT']} list", show_output=True)
    return

@virtual_cluster.command("version", help="Show the current vcluster version")
@add_options(_common_options)
@click.pass_obj
def version(ctx, main_context):
    """Returns vcluster version
    """
    sh.run_command(f"vcluster --version", show_output=True)
    return


@virtual_cluster.command("create", help="Create a vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@add_options(_common_options)
@click.pass_obj
def create(ctx, name, main_context):
    logger.info(f"Temporary helm values for vcluster will be stored in { TMP_VALUES_FILE }")
    # vcluster helm values
    values_data = {
        "rbac": {"clusterRole": {"create": True}},
        "vcluster": {"image": "rancher/k3s:v1.22.5-k3s1"},
        "syncer": {"extraArgs": ["--fake-nodes=false", "--sync-all-nodes"]},
    }
    
    # Store helm values
    with open(TMP_VALUES_FILE, "w") as file:
        yaml.dump(values_data, file, default_flow_style=False)
        
    # Create vcluster using helm values
    status_code, out = sh.run_command(
        f"vcluster --context {ctx['MAIN_CONTEXT']} create {name} -n {name} --expose -f {TMP_VALUES_FILE}"
    )
    if status_code != 0:
        logger.error(out)
        logger.error(f"Error creating the new vcluster. if it exists, try:\n\n fieldctl vm connect\n\n")
        raise click.Abort()
    
    # Update the current kubeconfig file with the new context
    kubeconfig_path = cluster.get_current_kubeconfig_path(ctx)
    cluster.connect_to_virtual_cluster(ctx, kubeconfig_path, name)
    logger.info(f"A new context has been created with name `{name}`. You will be switched to that context automatically\n\n")
    sh.run_command(
        f"kubectl --context {ctx['MAIN_CONTEXT']} config use-context {name}"
    )


@virtual_cluster.command("connect", help=f"Update current kubeconfig to connect to vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@add_options(_common_options)
@click.pass_obj
def connect(ctx, name, main_context):
    # Verify that the virtual cluster exists
    if not cluster.cluster_exist(ctx, name):
        logger.error(f"Cluster {name} does not exist")
        raise click.Abort()
    
    # Update the current kubeconfig file with context cluster name
    kubeconfig_path = cluster.get_current_kubeconfig_path(ctx)
    cluster.connect_to_virtual_cluster(ctx, kubeconfig_path, name)
    logger.info(f"A new context has been created with name `{name}`. You will be switched to that context automatically\n\n")
    
    # Switch context to cluster
    return_code, _ = sh.run_command(
        f"kubectl --context {ctx['MAIN_CONTEXT']} config use-context {name}"
    )
    if return_code != 0:
        logger.error(f"Error switching contexts")
        raise click.Abort()


@virtual_cluster.command("delete", help="Delete vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@add_options(_common_options)
@click.pass_obj
def delete(ctx, name, main_context):
    # Detele virtual cluster
    return_code, _ = sh.run_command(
        f"vcluster --context {ctx['MAIN_CONTEXT']} delete {name} -n {name}"
    )
    if return_code != 0:
        logger.error(f"Error deleting the vcluster")
        raise click.Abort()
    
    # It is needed to wait until virtual cluster is completely deleted
    cluster.wait_until_cluster_is_deleted(ctx, 20, name)
    logger.info(f"Delete related namespace {name} in main cluster {ctx['MAIN_CONTEXT']}")
    return_code, _ = sh.run_command(
        f"kubectl --context {ctx['MAIN_CONTEXT']} delete ns {name} --wait=false"
    )
    if return_code != 0:
        logger.error(f"Error deleting namespace. Please, fix manually in the cluster")
        raise click.Abort()
    
    # Remove the context from kubeconfig to keep the file clean
    kubeconfig_path = cluster.get_current_kubeconfig_path(ctx)
    logger.info(f"Remove virtual cluster context from kubeconfig: {kubeconfig_path}")
    cluster.remove_context_from_kubeconfig(kubeconfig_path, name)
    
    # Switch context to main cluster
    return_code, _ = sh.run_command(
        f"kubectl --context {ctx['MAIN_CONTEXT']} config use-context {ctx['MAIN_CONTEXT']}"
    )
    if return_code != 0:
        logger.error(f"Error switching contexts")
        raise click.Abort()
    logger.info(f"Context deleted. You are switched to main cluster context: {ctx['MAIN_CONTEXT']}")
