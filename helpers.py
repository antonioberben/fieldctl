import datetime
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time

import click
import click_log
import yaml

logger = logging.getLogger('root')

BINARIES_FOLDER = "binaries"
PROVISION_FOLDER = "provision"
HOME_VAR_NAME = "FIELDCTL_HOME"
TMP_KUBECONFIG = "/tmp/kubeconfig"
LIMA_CONFIG_TEMPLATE = "lima-vm.yaml.template"

def copy_persisted_folder(provision_folder, persisted_folder):
    shutil.copytree(
        f"{provision_folder}", f"{persisted_folder}", dirs_exist_ok=True
    )

def vm_exist(vm_name):
    _, out = new_run_command(f"limactl ls --json")
    out = ",".join(out.strip().split("\n"))
    out = "[" + out + "]"
    vms = json.loads(out)
    exist = len([i for i in vms if i["name"] == vm_name])
    return True if exist else False
        


def new_run_command(command, env=os.environ.copy(), show_output=False):
    logger.debug(f"Running command:\n{command}\n")
    if not show_output:
        process = subprocess.run(shlex.split(command), env=env, text=True, capture_output=True)
        output = process.stdout if process.stdout else process.stderr
        returncode = process.returncode
    else:
        logger.warn(f"###################################################################")
        logger.warn(f"Following output belongs to the binary being executed (limactl, vcluster, etc.). But its intructions might be misleading. Do not follow them if you are not familiar with the architecure")
        logger.warn(f"###################################################################")
        process = subprocess.Popen(shlex.split(command), env=env, text=True)
        output, _ = process.communicate()
    returncode = process.returncode        
    logger.debug('####### STDOUT #####')
    logger.debug(process.stdout)
    logger.debug('####### STDERR #####')
    logger.debug(process.stderr)
    logger.debug('####### END ########')
    return returncode, output

def run_command(command, stdout=None, env=os.environ.copy()):
    process = subprocess.run(shlex.split(command), env=env, text=True, capture_output=True)
    return process.returncode, process.stdout


def _get_current_path():
    resource_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return resource_path


def get_path_to_provision():
    resource_path = _get_current_path()
    provision_path = os.path.join(resource_path, PROVISION_FOLDER)
    return provision_path


def get_path_to_lima_template():
    resource_path = _get_current_path()
    path = os.path.join(resource_path, PROVISION_FOLDER, LIMA_CONFIG_TEMPLATE)
    return path


def cluster_exist(ctx, name):
    logger.info(f"Check if cluster exist")
    _, out = new_run_command(
        f"vcluster --context {ctx['KUBECONTEXT']} list --output json"
    )
    vclusters = json.loads(out)
    return len([i for i in vclusters if i["Name"] == name])


def wait_until_cluster_is_deleted(ctx, timeout_seconds, name):
    logger.info(f"Wait until cluster is deleted with timeout: {timeout_seconds}")
    in_waiting_seconds = datetime.datetime.now() + datetime.timedelta(
        0, timeout_seconds
    )
    while True:
        if datetime.datetime.now() > in_waiting_seconds:
            logger.error(
                f"Timeout. vcluster is not deleted. Please, fix manually with deleting the namespace {name} directly in the cluster"
            )
            raise click.Abort()
        if not cluster_exist(ctx, name):
            return
        time.sleep(1)


def add_home_persisted_folder(ctx, config):
    logger.info(f"Adding persisted volume {ctx['PERSISTED_FOLDER']} to {config}")
    with open(config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    data["mounts"].append({"location": ctx["PERSISTED_FOLDER"], "writable": True})
    data["env"][HOME_VAR_NAME] = ctx["PERSISTED_FOLDER"]
    with open(config, "w") as file:
        yaml.dump(data, file)


def update_allocated_resources(ctx, config, cpus, disk, memory):
    logger.info(f"Updating cpu to {cpus}")
    with open(config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    data["cpus"] = int(cpus)
    data["memory"] = f"{memory}Gib"
    data["disk"] = f"{disk}Gib"
    with open(config, "w") as file:
        yaml.dump(data, file)


def add_forwarded_port(ctx, config):
    logger.info(f"Adding forwarded port")
    with open(config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    data["portForwards"].append(
        {"guestPort": 6443, "hostPort": ctx["DEFAULT_PORT_FORWARD"]}
    )
    with open(config, "w") as file:
        yaml.dump(data, file)


def get_current_kubeconfig_path(ctx, kubeconfig=None):
    if kubeconfig is not None:
        return kubeconfig
    if "KUBECONFIG" in os.environ and len(os.environ["KUBECONFIG"]):
        return os.environ["KUBECONFIG"]
    return ctx["DEFAULT_KUBECONFIG"]


def _merge_kubeconfig_to(kubeconfig, path):
    logger.info(f"Merge new context to {path}")
    if not os.path.isfile(path):
        logger.warn(f"No config found in {path}. Create directly a new one")
        with open(path, "w") as file:
            yaml.dump(kubeconfig, file, default_flow_style=False)
        return
        
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
    return_code, out = new_run_command(
        f"vcluster --context {ctx['KUBECONTEXT']} connect {name} -n {name} --print --silent"
    )
    if return_code != 0:
        logger.error(
            f"Error retreiving the kubeconfig. Check in the cluster the status of the vcluster pod. Or try:\n\n  fieldctl cluster connect --name {name}"
        )
        raise click.Abort()
    vcluster_cluster_config = yaml.load(out, Loader=yaml.FullLoader, )
    vcluster_cluster_config = _update_context_name(vcluster_cluster_config, name)
    _merge_kubeconfig_to(vcluster_cluster_config, kubeconfig_path)


def connect_to_main_cluster(ctx, kubeconfig_path):
    returncode, out = new_run_command(
        f"limactl shell --workdir='/' {ctx['VM_NAME']} sudo cat /etc/rancher/k3s/k3s.yaml")
    if returncode != 0:
        logger.error(out)
        raise click.Abort()
    main_cluster_config = yaml.load(out, Loader=yaml.FullLoader)
    main_cluster_config = _update_context_name(main_cluster_config, ctx["VM_NAME"])
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
