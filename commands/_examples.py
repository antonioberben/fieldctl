import click
import os

def my_callback(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version 1.0')
    ctx.exit()

@click.command(help="Examples to develop commands.")
@click.option('--flag-example-1', default=False, help='This is a flag parameter with default value')
@click.option('--flag-example-2', is_flag=True, help='This is a flag parameter')
@click.option('--flag-example-2', is_flag=True, help='This is a flag parameter')
@click.option('--name', prompt=True, help='This is prompt parameter')
@click.option(
    "--password", prompt=True, hide_input=True,
    confirmation_prompt=True,
    help='This is a password prompt'
)
@click.option(
    "--username", prompt=True,
    default=lambda: os.environ.get("USER", ""),
    show_default="current user",
    help='This is either a prompt or a value taken form the given env var'
)
@click.option('--option',
              type=click.Choice(['option1', 'option2'], case_sensitive=False))
@click.option('--my-callback', is_flag=True, callback=my_callback,
              expose_value=False, is_eager=True, 
              help='This is to create a callback function to be triggered when flag paramter is given')
def demo(flag_example_1, flag_example_2, option):
    print(f'test')