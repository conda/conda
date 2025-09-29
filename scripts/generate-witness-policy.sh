#!/bin/bash
# Generate witness policy for testing

cat > build-policy.yaml << 'EOF'
expires: "2025-12-31T23:59:59Z"
steps:
  - name: conda-package-build
    attestations:
      - type: https://witness.dev/attestations/command-run/v0.1
        regopolicies:
          - name: exit-zero
            module: |
              package commandrun
              default allow = false
              allow { input.exitcode == 0 }
      - type: https://witness.dev/attestations/product/v0.1
        regopolicies:
          - name: wheel-created
            module: |
              package product
              default allow = false
              allow {
                some i
                contains(input[i].name, ".whl")
              }
      - type: https://witness.dev/attestations/github/v0.1
        regopolicies:
          - name: github-build
            module: |
              package github
              default allow = false
              allow {
                input.workflow != ""
                input.repository == "testifysec/conda"
              }
      - type: https://witness.dev/attestations/environment/v0.1
      - type: https://witness.dev/attestations/git/v0.1
      - type: https://witness.dev/attestations/material/v0.1
EOF

echo "Test policy generated: build-policy.yaml"