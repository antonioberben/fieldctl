#!/usr/bin/env python3

import click
import sys
import os
import time
import helpers

# from commands._examples import _examples
from commands.cluster import cluster
from commands.vm import vm


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.obj["DEBUG"] = debug
    vm_name = "field-vm"
    ctx.obj["VM_NAME"] = vm_name
    ctx.obj["KUBECONTEXT"] = vm_name
    ctx.obj["PERSISTED_FOLDER"] = os.environ.get("HOME") + "/.field"
    ctx.obj["DEFAULT_KUBECONFIG"] = os.environ.get("HOME") + "/.kube/config"
    ctx.obj["DEFAULT_PORT_FORWARD"] = 11443
    ctx.obj["PROVISION_FOLDER"] = helpers.get_path_to_provision()
    ctx.obj["LIMA_TEMPLATE"] = helpers.get_path_to_lima_template()


#### Add the command here ####
# cli.add_command(_examples)
cli.add_command(cluster)
cli.add_command(vm)
##############################


if __name__ == "__main__":
    cli(obj={})

