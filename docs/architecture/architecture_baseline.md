# Architecture Baseline v0.1

## Principles

- Architecture first, feature second.
- Constraints drive workflow behavior.
- Every critical workflow output must be auditable.

## Core Layers

1. Constraints Layer
2. Workflow Layer
3. Artifact Layer
4. Verification Layer

## Mandatory Checks

- `constraints` version is present in every workflow summary.
- Memory outputs reference source evidence IDs.
- Cross-workflow decisions are replayable by artifact trail.

## Branch Policy

- `main`: architecture-gated stable baseline.
- Feature branches must pass architecture checks before merge.
