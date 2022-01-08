import logging
import os
import shlex
import subprocess
import re
import time
import click_log

logger = logging.getLogger('root')


def run_command(command, env=os.environ.copy(), show_output=False):
    logger.debug(f"Running command:\n{command}")
    if not show_output:
        process = subprocess.run(shlex.split(command), env=env, text=True, capture_output=True)
        returncode = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    else:
        logger.warning(f"[BEGIN - IGNORE THIS BLOCK]-----------------------------------------------------")
        logger.warning(f"Following output belongs to the binary being executed (limactl, vcluster, etc.). But its intructions might be misleading. Do not follow them if you are not familiar with the architecure")
        process = subprocess.Popen(shlex.split(command), env=env)
        stdout, stderr = process.communicate()
        logger.warning(f"[END - IGNORE THIS BLOCK]-----------------------------------------------------\n")
    returncode = process.returncode
    logger.debug(f'RETURNCODE: {returncode}\nSTDOUT:\n{strip_ansi(stdout)}\nSTDERR:\n{strip_ansi(stderr)}')
    return returncode, stderr if stderr else stdout

def get_process_output(process):
    time.sleep(1)
    while True:
        output = process.stdout.readline()
        print(output.strip())
        # Do something else
        return_code = process.poll()
        if return_code is not None:
            print('RETURN CODE', return_code)
            # Process has finished, read rest of the output 
            for output in process.stdout.readlines():
                print(output.strip())
            break
    return output

def strip_ansi(source):
    """
    Remove ansi escape codes from text.
    
    Parameters
    ----------
    source : str
        Source to remove the ansi from
    """
    return re.sub(r'\033\[(\d|;)+?m', '', source) if source else ""