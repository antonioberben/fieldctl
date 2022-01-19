#!/usr/bin/env python3

import click
import sys
import os
import logging
import log

# from commands._examples import _examples
from commands.virtual_cluster import virtual_cluster
from commands.vm import vm

import helpers.vm_helper as vmh

VERSION_FILE="version.txt"


@click.group()
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
)
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
    
    \b
            fieldctl vm create
            fieldctl vm connect
    \b
            # With --log-level:
            fieldctl -l DEBUG vm stop        
            fieldctl -l DEBUG vm start
    \b
            # Create two virtual clusters:
            fieldctl virtual create -n demo-1
            fieldctl virtual create -n demo-2
            
    \b
            # You do not need the VM. You can use your own main cluster:
    \b
            ## Create a vcluster having the current context as main cluster
            fieldctl virtual create -n demo-2 -ctx
    \b
            ## Create a vcluster having the given context as main cluster
            fieldctl virtual create -n demo-2 -ctx <my-main-cluster-context>
    """
    # Update log_level in logger
    if isinstance(log_level, str):
        loglevel = getattr(logging, log_level.upper())
    logger = log.setup_custom_logger("root", loglevel)
    if logger.getEffectiveLevel() < logging.INFO:
        logger.warning(f"LOG_LEVEL: {log_level}")
    # Add context values
    ctx.obj["MAIN_CONTEXT"] = "field-main"
    ctx.obj["PERSISTED_FOLDER"] = os.environ.get("HOME") + "/.field"
    ctx.obj["DEFAULT_KUBECONFIG"] = os.environ.get("HOME") + "/.kube/config"
    ctx.obj["DEFAULT_PORT_FORWARD"] = 11443
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ctx.obj["PROVISION_FOLDER"] = vmh.get_path_to_provision(base_path)
    ctx.obj["LIMA_TEMPLATE"] = vmh.get_path_to_lima_template(base_path)
    
@cli.command("version", help="Displays current fieldctl version")
@click.pass_obj
def version(ctx):
    with open(VERSION_FILE, "r") as file:
        click.echo(f'{file.read()}')
    return


#### Add the command here ####
# cli.add_command(_examples)
cli.add_command(vm)
cli.add_command(virtual_cluster)
##############################

# This solves https://github.com/pallets/click/issues/456#issuecomment-159543498
def main():
    return cli(obj={})

if __name__ == "__main__":
    main()

