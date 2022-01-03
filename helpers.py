import logging
import subprocess
import shlex
import click_log
import os
import sys
import time
import click
import datetime
import json
import yaml
import shutil

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
click_log.basic_config(logger)

BINARIES_FOLDER = "binaries"
PROVISION_FOLDER = "provision"
HOME_VAR_NAME = "SOLO_FIELD_HOME"
TMP_KUBECONFIG = "/tmp/kubeconfig"
LIMA_CONFIG_TEMPLATE = "lima-vm.yaml.template"


def run_command(command, stdout=None, env=os.environ.copy()):
    process = subprocess.Popen(shlex.split(command), stdout=stdout, env=env, text=True)
    output, _ = process.communicate()
    return process.returncode, output


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
    _, out = run_command(
        f"vcluster --context {ctx['KUBECONTEXT']} list --output json", stdout=subprocess.PIPE
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
        _, out = run_command(
            f"vcluster --context {ctx['KUBECONTEXT']} list --output json", stdout=subprocess.PIPE
        )
        vclusters = json.loads(out)
        if not len([i for i in vclusters if i["Name"] == name]):
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


def add_forwarded_port(ctx, config):
    logger.info(f"Adding forwarded port")
    with open(config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    data["portForwards"].append(
        {"guestPort": 6443, "hostPort": ctx["DEFAULT_PORT_FORWARD"]}
    )
    with open(config, "w") as file:
        yaml.dump(data, file)


def get_current_kubeconfig_path(ctx, kubeconfig):
    if kubeconfig is not None:
        return kubeconfig
    if "KUBECONFIG" in os.environ and len(os.environ["KUBECONFIG"]):
        return os.environ["KUBECONFIG"]
    return ctx["DEFAULT_KUBECONFIG"]


def merge_k3s_kubeconfig(ctx, config_path, current, new):
    if len(current["clusters"]) == 0:
        with open(config_path, "w") as file:
            yaml.dump(new, file, default_flow_style=False)
        return
    # First delete
    for i, cluster in enumerate(current["clusters"]):
        if cluster["name"] == ctx["VM_NAME"]:
            current["clusters"].pop(i)
    for i, context in enumerate(current["contexts"]):
        if context["name"] == ctx["VM_NAME"]:
            current["contexts"].pop(i)
    for i, user in enumerate(current["users"]):
        if user["name"] == ctx["VM_NAME"]:
            current["users"].pop(i)
    # Now append
    current["clusters"].append(new["clusters"][0])
    current["contexts"].append(new["contexts"][0])
    current["users"].append(new["users"][0])
    current["current-context"] = ctx["VM_NAME"]
    dt = datetime.datetime.now()
    ts = datetime.datetime.timestamp(dt)
    shutil.copy(config_path, config_path + "_" + str(ts))
    with open(config_path, "w") as file:
        yaml.dump(current, file, default_flow_style=False)


def connect_to_cluster(ctx, current_kubeconfig):
    with open(TMP_KUBECONFIG, "w") as file:
        returncode, _ = run_command(
            f"limactl shell --workdir='/' {ctx['VM_NAME']} sudo cat /etc/rancher/k3s/k3s.yaml",
            stdout=file,
        )
        if returncode != 0:
            logger.error("Error retrieving k3s cluster config")
            raise click.Abort()
    with open(TMP_KUBECONFIG, "r") as file:
        k3s_kubeconfig = yaml.load(file, Loader=yaml.FullLoader)
    k3s_kubeconfig["clusters"][0]["name"] = ctx["VM_NAME"]
    k3s_kubeconfig["clusters"][0]["cluster"][
        "server"
    ] = f"https://127.0.0.1:{ctx['DEFAULT_PORT_FORWARD']}"
    k3s_kubeconfig["clusters"][0]["cluster"]["name"] = ctx["VM_NAME"]
    k3s_kubeconfig["contexts"][0]["name"] = ctx["VM_NAME"]
    k3s_kubeconfig["contexts"][0]["context"]["cluster"] = ctx["VM_NAME"]
    k3s_kubeconfig["contexts"][0]["context"]["user"] = ctx["VM_NAME"]
    k3s_kubeconfig["users"][0]["name"] = ctx["VM_NAME"]
    k3s_kubeconfig["current-context"] = ctx["VM_NAME"]
    current_config_path = get_current_kubeconfig_path(ctx, current_kubeconfig)
    logger.info(f"Current kubeconfig: {current_config_path}")
    if not os.path.isfile(current_config_path):
        with open(current_config_path, "w") as file:
            yaml.dump(k3s_kubeconfig, file, default_flow_style=False)
        return
    with open(current_config_path, "r") as file:
        current_k3s_kubeconfig = yaml.load(file, Loader=yaml.FullLoader)
    merge_k3s_kubeconfig(
        ctx, current_config_path, current_k3s_kubeconfig, k3s_kubeconfig
    )
    logger.info(f"Context {ctx['VM_NAME']} has been merged to {current_config_path}")
