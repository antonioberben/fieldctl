#!/usr/bin/env python3

import click
import sys
import os
import time
import helpers
import logging
import log
logger = log.setup_custom_logger('root')
from click_loglevel import LogLevel

# from commands._examples import _examples
from commands.cluster import cluster
from commands.vm import vm



@click.group()
@click.option("--log-level", '-l', type=LogLevel(), default=logging.INFO)
@click.pass_context
def cli(ctx, log_level):
    """This CLI is intended to be a wrapper for other tools like limactl, vcluster, metallb, etc.
    
    Given the complexity of all the underlying tools, this CLI serves as interface for engineers to quickly
    spin up clusters and destroy them continuously.
    
    The CLI was tested with versions:
    
    vcluster 0.4.5
    
    limactl 0.7.3
    
    For more information go to the official repository: https://github.com/antonioberben/fieldctl
    
    Please, do not hesitate to collaborate!
    
    Examples:
    
    fieldctl vm create
    
    fieldctl vm connect
    
    # Create two virtual clusters
    
    fieldctl cluster create -n demo-1
    
    fieldctl cluster create -n demo-2
    
    # With --log-level
    
    fieldctl -l DEBUG vm stop
    
    fieldctl -l DEBUG vm start
    """
    logger.setLevel(log_level)
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
cli.add_command(vm)
cli.add_command(cluster)
##############################


if __name__ == "__main__":
    cli(obj={})

