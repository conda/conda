# Witness
[![Go Reference](https://pkg.go.dev/badge/github.com/in-toto/witness.svg)](https://pkg.go.dev/github.com/in-toto/witness) [![Go Report Card](https://goreportcard.com/badge/github.com/in-toto/witness)](https://goreportcard.com/report/github.com/in-toto/witness) [![OpenSSF Best Practices](https://www.bestpractices.dev/projects/8164/badge)](https://www.bestpractices.dev/projects/8164) [![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/in-toto/witness/badge)](https://securityscorecards.dev/viewer/?uri=github.com/in-toto/witness) [![FOSSA Status](https://app.fossa.com/api/projects/custom%2B41709%2Fgithub.com%2Fin-toto%2Fwitness.svg?type=shield&issueType=license)](https://app.fossa.com/projects/custom%2B41709%2Fgithub.com%2Fin-toto%2Fwitness?ref=badge_shield&issueType=license)

<center>

**[DOCS](https://witness.dev) •
[CONTRIBUTING](/CONTRIBUTING.md) •
[LICENSE](https://github.com/in-toto/witness/blob/main/LICENSE)**

`bash <(curl -s https://raw.githubusercontent.com/in-toto/witness/main/install-witness.sh)`
</center>

<img src="https://raw.githubusercontent.com/in-toto/witness/main/docs/assets/logo.png" align="right"
     alt="Witness project logo" width="200"></img>

### What does Witness do?
✏️ **Attests** - <span class="tip-text">Witness is a dynamic CLI tool that integrates into pipelines and infrastructure to create an
audit trail for your software's entire journey through the software development lifecycle (SDLC) using the in-toto specification.</span>

**🧐 Verifies** - <span class="tip-text">Witness also features its own policy engine with embedded support for OPA Rego, so you can
ensure that your software was handled safely from source to deployment.</span>

### What can you do with Witness?
- Verify how your software was produced and what tools were used
- Ensure that each step of the supply chain was completed by authorized users and machines
- Detect potential tampering or malicious activity
- Distribute attestations and policy across air gaps

### Key Features
 - Integrations with GitLab, GitHub, AWS, and GCP.
 - Designed to run in both containerized and non-containerized environments **without** elevated privileges.
 - Implements the in-toto specification (including ITE-5, ITE-6 and ITE-7)
 - An embedded OPA Rego policy engine for policy enforcement
 - Keyless signing with Sigstore and SPIFFE/SPIRE
 - Integration with RFC3161 compatible timestamp authorities
 - Process tracing and process tampering prevention (Experimental)
- Attestation storage with [Archivista](https://github.com/in-toto/archivista)

### Demo
![Demo][demo]

## Quick Start

### Installation
To install Witness, all you will need is the Witness binary. You can download this from the [releases](https://github.com/in-toto/witness/releases) page or use the install script to download the
latest release:
```
bash <(curl -s https://raw.githubusercontent.com/in-toto/witness/main/install-witness.sh)
```

If you want install it manually and verify its integrity follow the instructions in the [INSTALL.md](./INSTALL.md).

### Tutorials
Check out our Tutorials:

- [Getting Started](docs/tutorials/getting-started.md)
- [Verify an Artifact Policy](docs/tutorials/artifact-policy.md)
- [Using Fulcio as a Key Provider](docs/tutorials/artifact-policy.md)

## Media
Check out some of the content out in the wild that gives more detail on how the project can be used.

##### [Blog/Video - Generating and Verifying Attestations With Witness](https://www.testifysec.com/blog/attestations-with-witness/)
##### [Blog - What is a supply chain attestation, and why do I need it?](https://www.testifysec.com/blog/what-is-a-supply-chain-attestation/)
##### [Talk - Securing the Software Supply Chain with the in-toto & SPIRE projects](https://www.youtube.com/watch?v=4lFbdkB62QI)
##### [Talk - Securing the Software Supply Chain with SBOM and Attestation](https://www.youtube.com/watch?v=wX6aTZfpJv0)

## Get Involved with the Community!
Join the [CNCF Slack](https://slack.cncf.io/) and join the `#in-toto-witness` channel. You might also be interested in joining the `#in-toto` channel for more general in-toto discussion, as well as
the `#in-toto-archivista` channel for discussion regarding the [Archivista](https://github.com/in-toto/archivista) project.

## Background
This project was created by [TestifySec](https://www.testifysec.com/) before being donated to the in-toto project. The project is maintained by the TestifySec Open Source team and a community of contributors.

[demo]: https://raw.githubusercontent.com/in-toto/witness/main/docs/assets/demo.gif "Demo"
