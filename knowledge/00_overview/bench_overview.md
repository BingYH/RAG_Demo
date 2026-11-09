---
doc_id: bench.overview
title: Demo Bench v1 architecture and diagnostic scope
version: "1.0"
status: current
source_type: synthetic
applies_to: [demo-bench-v1]
source_ids: [FCI-OVERVIEW]
---

# Demo Bench v1 architecture and diagnostic scope

## Applicability

This is a fictional engineering support bench, inspired by public Franka documentation. All bench identifiers, versions, addresses, states and procedures below are synthetic. Demo Client is not libfranka; Demo Controller does not implement the real FCI protocol.

## Components

`BENCH-001` contains an Ubuntu 24.04 workstation, Demo Client, a dedicated Ethernet connection, Demo Controller and a fictional seven-joint arm named `DEMO-ARM-7`. The workstation starts the client, loads its configuration, establishes a connection, negotiates compatibility and reads controller state.

ROS 2 Jazzy is the architectural background only. This release reads local fixtures; it does not launch ROS nodes or drive a robot. A missing ROS observation must be reported as not collected, not as evidence that ROS is broken.

## What diagnostic readiness means

The terminal initialization stage `diagnostic_ready` means configuration loading, endpoint reachability, handshake acceptance and state reception succeeded for the recorded attempt. It does not certify motion readiness, calibration, safety approval or completion of functional tests.

If a user reports a failure but the available snapshot is ready, compare the reported incident time and attempt with the snapshot. Request a matching observation or reproduction details; do not dismiss the report.

## Evidence boundaries

An asset register describes an expected configuration and can be outdated. Runtime configuration describes what the client actually loaded. Connection observations describe the checked endpoint. None can substitute for another without explanation.

The assistant may read observations and prepare a support ticket. It must not claim to have repaired the bench, changed networking, installed software or tested real motion.

## Public background

FCI-OVERVIEW, `docs/source/overview.rst`, sections on the interface architecture and framework support, explains the real workstation-to-controller concept. This document applies that concept to a fictional diagnostic bench; it makes no claim about an employer's equipment. Exact reference commits are recorded in `docs/source_manifest.json` outside the retrieval corpus.
