import json
import logging
import os
import shutil
import sys
import yaml

import helpers.shell_helper as sh

logger = logging.getLogger('root')

PROVISION_FOLDER = "provision"
HOME_VAR_NAME = "FIELDCTL_HOME"
LIMA_CONFIG_TEMPLATE = "lima-vm.yaml.template"

def copy_persisted_folder(provision_folder, persisted_folder):
    shutil.copytree(
        f"{provision_folder}", f"{persisted_folder}", dirs_exist_ok=True
    )
    
def vm_exist(vm_name):
    _, out = sh.run_command(f"limactl ls --json")
    out = ",".join(out.strip().split("\n"))
    out = "[" + out + "]"
    vms = json.loads(out)
    exist = len([i for i in vms if i["name"] == vm_name])
    return True if exist else False


def get_path_to_provision(base_path):
    provision_path = os.path.join(base_path, PROVISION_FOLDER)
    return provision_path

def get_path_to_lima_template(base_path):
    path = os.path.join(base_path, PROVISION_FOLDER, LIMA_CONFIG_TEMPLATE)
    return path

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
