import datetime
import json
import logging
import os
import shutil
import time

import click
import yaml
import helpers.shell_helper as sh

logger = logging.getLogger('root')

def cluster_exist(ctx, name):
    # Verify that the cluster exist
    logger.info(f"Check if cluster exist")
    _, out = sh.run_command(
        f"vcluster --context {ctx['MAIN_CONTEXT']} list --output json"
    )
    vclusters = json.loads(out)
    # If the virtual cluster is found, the length is greater than 0
    return len([i for i in vclusters if i["Name"] == name])

def wait_until_cluster_is_deleted(ctx, timeout_seconds, name):
    logger.info(f"Wait until cluster is deleted with timeout: {timeout_seconds} seconds")
    in_waiting_seconds = datetime.datetime.now() + datetime.timedelta(
        0, timeout_seconds
    )
    # Iterate until either cluster does not exist or timeout
    while True:
        if datetime.datetime.now() > in_waiting_seconds:
            logger.error(
                f"Timeout. vcluster is not deleted. Please, fix manually with deleting the namespace {name} directly in the cluster"
            )
            raise click.Abort()
        if not cluster_exist(ctx, name):
            return
        time.sleep(1)

def get_current_kubeconfig_path(ctx, kubeconfig=None):
    # Get the current kubeconfig from a given path, $KUBECONFIG env var or `~/.kube/config`
    if kubeconfig is not None:
        return kubeconfig
    if "KUBECONFIG" in os.environ and len(os.environ["KUBECONFIG"]):
        return os.environ["KUBECONFIG"]
    return ctx["DEFAULT_KUBECONFIG"]

def _merge_kubeconfig_to(kubeconfig, path):
    logger.info(f"Merge new context to {path}")
    
    # If the kubeconfig does not exist, create the new one directly and exit
    if not os.path.isfile(path):
        logger.warning(f"No config found in {path}. Create directly a new one")
        with open(path, "w") as file:
            yaml.dump(kubeconfig, file, default_flow_style=False)
        return
        
    # If the kubeconfig already exist, merge with the new one
    with open(path, "r") as file:
        current_kubeconfig = yaml.load(file, Loader=yaml.FullLoader)

    new_context_name = kubeconfig["clusters"][0]["cluster"]["name"]
    new_cluster = kubeconfig["clusters"][0]
    new_context = kubeconfig["contexts"][0]
    new_user = kubeconfig["users"][0]
    current_kubeconfig = _merge_config_cluster(
        current_kubeconfig, new_context_name, new_cluster
    )
    current_kubeconfig = _merge_config_context(
        current_kubeconfig, new_context_name, new_context
    )
    current_kubeconfig = _merge_config_user(
        current_kubeconfig, new_context_name, new_user
    )
    current_kubeconfig["current-context"] = new_context_name
    
    # Backup the old kubeconfig before saving
    _backup_current_kubeconfig(path)
    with open(path, "w") as file:
        yaml.dump(current_kubeconfig, file, default_flow_style=False)

def _backup_current_kubeconfig(path):
    dt = datetime.datetime.now()
    ts = datetime.datetime.timestamp(dt)
    shutil.copy(path, path + "_" + str(ts))

def _merge_config_user(current_kubeconfig, new_context_name, new_user):
    for i, user in enumerate(current_kubeconfig["users"]):
        if user["name"] == new_context_name:
            current_kubeconfig["users"].pop(i)
    current_kubeconfig["users"].append(new_user)
    return current_kubeconfig


def _merge_config_context(current_kubeconfig, new_context_name, new_context):
    for i, context in enumerate(current_kubeconfig["contexts"]):
        if context["name"] == new_context_name:
            current_kubeconfig["contexts"].pop(i)
    current_kubeconfig["contexts"].append(new_context)
    return current_kubeconfig


def _merge_config_cluster(current_kubeconfig, new_context_name, new_cluster):
    for i, cluster in enumerate(current_kubeconfig["clusters"]):
        if cluster["name"] == new_context_name:
            current_kubeconfig["clusters"].pop(i)
    current_kubeconfig["clusters"].append(new_cluster)
    return current_kubeconfig

def connect_to_virtual_cluster(ctx, kubeconfig_path, name):
    logger.debug("Retrieve vcluster kubeconfig")
    return_code, out = sh.run_command(
        f"vcluster --context {ctx['MAIN_CONTEXT']} connect {name} -n {name} --print --silent"
    )
    if return_code != 0:
        logger.error(
            f"Error retreiving the kubeconfig. Check in the cluster the status of the vcluster pod. Or try:\n\n  fieldctl virtual connect --name {name}"
        )
        raise click.Abort()
    vcluster_cluster_config = yaml.load(out, Loader=yaml.FullLoader, )
    vcluster_cluster_config = _update_context_name(vcluster_cluster_config, name)
    _merge_kubeconfig_to(vcluster_cluster_config, kubeconfig_path)

def connect_to_main_cluster(ctx, kubeconfig_path):
    returncode, out = sh.run_command(
        f"limactl shell --workdir='/' {ctx['MAIN_CONTEXT']} sudo cat /etc/rancher/k3s/k3s.yaml")
    if returncode != 0:
        logger.error(out)
        raise click.Abort()
    main_cluster_config = yaml.load(out, Loader=yaml.FullLoader)
    main_cluster_config = _update_context_name(main_cluster_config, ctx["MAIN_CONTEXT"])
    
    # The main cluster server host is localhost + the a port given in the lima VM template
    main_cluster_config = _update_context_server(
        main_cluster_config, f"https://127.0.0.1:{ctx['DEFAULT_PORT_FORWARD']}"
    )
    _merge_kubeconfig_to(main_cluster_config, kubeconfig_path)
    
    
def _update_context_server(kubeconfig, server):
    kubeconfig["clusters"][0]["cluster"]["server"] = server
    return kubeconfig


def _update_context_name(kubeconfig, name):
    kubeconfig["clusters"][0]["name"] = name
    kubeconfig["clusters"][0]["cluster"]["name"] = name
    kubeconfig["contexts"][0]["name"] = name
    kubeconfig["contexts"][0]["context"]["cluster"] = name
    kubeconfig["contexts"][0]["context"]["user"] = name
    kubeconfig["users"][0]["name"] = name
    kubeconfig["current-context"] = name
    return kubeconfig

def remove_context_from_kubeconfig(path, name):
    with open(path, "r") as file:
        try:
            kubeconfig = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            logger.error(f"{exc}")
            raise click.Abort()
    for i, user in enumerate(kubeconfig["users"]):
        if user["name"] == name:
            kubeconfig["users"].pop(i)
    for i, cluster in enumerate(kubeconfig["clusters"]):
        if cluster["name"] == name:
            kubeconfig["clusters"].pop(i)
    for i, context in enumerate(kubeconfig["contexts"]):
        if context["name"] == name:
            kubeconfig["contexts"].pop(i)
    with open(path, "w") as file:
        yaml.dump(kubeconfig, file, default_flow_style=False)
        