# Fieldctl CLI

This cli aims to help on operating a local environment. The intention is to wrap some complicated commands which are used to develop in local.

The first target is MacOS.

## Background

You usually need to create ephemeral environments quickly to develop, test and debug.

These actions can occur quite often. And, in some cases, you rather prefer a clean environment than an already used one.

Every time a new instance of the cluster is needed, you need to destroy de cluster and re-create it.

In a Linux OS with some flavours of k8s (kind, k3s, k0s), these actions can take a small period of time.

In a MacOS, you might need to create a VM, making the repetitive process a time consumer (1 minute  each time can be quite annoying)

This CLI helps on making easy to create a VM with a k8s cluster (k3s) and deploy vclusters.

[Vcluster](https://www.vcluster.com/) is a technology which allows to have multiple isolated k8s clusters within one "main" one.

Creating and deleting those `vclusters` is a matter of seconds. This helps on speeding up the development lifecycle.

## How to use

The CLI is pretty simple and right to the point.

Download it and run:

```bash
<cli> --help
<cli> vm --help
<cli> cluster --help
```

### Dependencies

The binary is shipped with `vcluster` embedded.

The cli requires you to have installed `lima VM` and `kubectl`.

## DEV Notes

**Why python?** The CLI could have been developed using any other language. However, python is easy to read and develop even not having much experience.

As well, one of the packages is [pyinstaller](https://github.com/pyinstaller/pyinstaller) which facilitates the creation of the binary.

**Why click?** click is a python framework to develop CLIs. It is extremely friendly an intuitive making the development of your CLI quite easy to anybody to understand it and to collaborate.

The downside is on execution time. In order to run, the binary creates a temporary folder in your filesystem to deploy the embedded resources like the template. This creates a small latency the first time is executed.

Notice that:

- Work in progress. The cli is open to grow in any direction. For example: Add commands to test scenarios
- No tests created. Being first iterations, there are no test to cover the results.
- Code is not polished. Being firsts iterations, the code is still dirty

## Acknowledgements

Fieldctl is built upon other open source code projects. Without these projects Fieldctl would never have seen the light.

- [Lima VM](https://github.com/lima-vm/lima)
- [Vcluster](https://github.com/loft-sh/vcluster)
- [k3s](https://github.com/k3s-io/k3s)
- [MetalLB](https://github.com/metallb/metallb)
