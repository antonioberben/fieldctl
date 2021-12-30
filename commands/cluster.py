import subprocess
import click
import logging
import yaml
import time
import datetime
import helpers
import click_log
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
click_log.basic_config(logger)

TMP_VALUES_FILE = "/tmp/vcluster-values.yaml"


@click.group()
@click.pass_obj
def cluster(ctx):
    """Configure cluster using vcluster (https://www.vcluster.com/)
    
    TIPS:
    
    - Mind the resources (CPU and memory) for the VM when creating many clusters
    """
    returncode, _ = helpers.run_command(f"which { ctx['vcluster'] }", stdout=subprocess.PIPE)
    if returncode != 0:
        logger.error(
            f"You need to install vcluster (https://www.vcluster.com/docs/getting-started/setup#download-vcluster-cli)"
        )
        raise click.Abort()
    returncode, _ = helpers.run_command("which kubectl", stdout=subprocess.PIPE)
    if returncode != 0:
        logger.error(
            f"You need to install kubectl (https://kubernetes.io/docs/tasks/tools/)"
        )
        raise click.Abort()
    pass


@cluster.command("list", help=f"List all vclusters in the context")
@click.pass_obj
def list(ctx):
    helpers.run_command(f"{ ctx['vcluster'] } list")
    return


@cluster.command("version", help="Show the current vlcuster version")
@click.pass_obj
def version(ctx):
    helpers.run_command(f"{ ctx['vcluster'] } --version")
    return


@cluster.command("create", help="Create a vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@click.pass_obj
def create(ctx, name):
    logger.info(f"Temporary values will be stored in { TMP_VALUES_FILE }")
    values_data = {
        "rbac": {"clusterRole": {"create": True}},
        "vcluster": {"image": "rancher/k3s:v1.21.4-k3s1"},
        "syncer": {"extraArgs": ["--fake-nodes=false", "--sync-all-nodes"]},
    }
    with open(TMP_VALUES_FILE, "w") as file:
        yaml.dump(values_data, file, default_flow_style=False)
    status_code, _ = helpers.run_command(
        f"{ ctx['vcluster'] } --context {ctx['KUBECONTEXT']} create {name} -n {name} --expose -f {TMP_VALUES_FILE}"
    )
    if status_code != 0:
        logger.error(f"Error creating the new vcluster")
        raise click.Abort()
    logger.info("Update kube config file with new vcluster context")
    return_code, _ = helpers.run_command(
        f"{ ctx['vcluster'] } --context {ctx['KUBECONTEXT']} connect {name} -n {name} --update-current"
    )
    if return_code != 0:
        logger.error(
            f"Error retreiving the kubeconfig. Check in the cluster the status of the vcluster pod. Or try with `<binary> cluster connect --name {name}"
        )
        raise click.Abort()
    
    logger.info(f"A new context has been created with name `vcluster_{name}_{name}`. You will be switched to that context automatically\n\n")
    helpers.run_command(
        f"kubectl --context {ctx['KUBECONTEXT']} config use-context vcluster_{name}_{name}"
    )


@cluster.command("connect", help=f"Update current kubeconfig to connect to vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@click.pass_obj
def connect(ctx, name):
    if not helpers.cluster_exist(ctx, name):
        logger.error(f"Cluster {name} does not exist")
        raise click.Abort()
    logger.info("Update kube config file with new vcluster context")
    helpers.run_command(
        f"{ ctx['vcluster'] } --context {ctx['KUBECONTEXT']} connect {name} -n {name} --update-current"
    )
    logger.info(f"You will be switched to the context automatically\n\n")
    helpers.run_command(
        f"kubectl --context {ctx['KUBECONTEXT']} config use-context vcluster_{name}_{name}"
    )


@cluster.command("delete", help="Delete vcluster")
@click.option("--name", "-n", required=True, help="Name for the environment")
@click.pass_obj
def delete(ctx, name):
    return_code, _ = helpers.run_command(
        f"{ ctx['vcluster'] } --context {ctx['KUBECONTEXT']} delete {name} -n {name}"
    )
    if return_code != 0:
        logger.error(f"Error deleting the vcluster")
        raise click.Abort()
    helpers.wait_until_cluster_is_deleted(ctx, 20, name)
    logger.info(f"Delete related namespace {name}")
    return_code, _ = helpers.run_command(
        f"kubectl --context {ctx['KUBECONTEXT']} delete ns {name} --wait=false"
    )
    if return_code != 0:
        logger.error(f"Error deleting namespace. Please, fix manually in the cluster")
        raise click.Abort()
