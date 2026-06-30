# OTPORSApp: Decision Support for Sustainable Mobility

*Hochschule Esslingen — ANOMOB Project*

## Overview

OTPORSApp is a decision-support application built as part of the ANOMOB project at Hochschule Esslingen, which investigates privacy-preserving and efficient mobility solutions. The project's core research question is how to help travelers balance two often competing priorities: travel efficiency and environmental impact. OTPORSApp is the practical implementation of that research, giving users a transparent, data-driven basis for choosing between transport modes using real-time transit data and environmental metrics.

## Infrastructure & Deployment

- **Docker containerization.** Deployed OpenRouteService (ORS) and OpenTripPlanner (OTP) as Docker containers, giving the backend a modular, reproducible, and scalable foundation that can be redeployed across environments without manual reconfiguration.
- **Service integration.** Unified two independent routing engines — ORS for car-based routing and OTP for public transport — behind a single decision-support interface, abstracting away their differing data models and APIs.

## Core Technologies

- **OpenTripPlanner (OTP)** — multi-modal public transport routing engine.
- **GTFS (General Transit Feed Specification)** — consumed under the hood to drive accurate public transport schedules and route calculations.
- **OS Open Services** — used for car-based routing and distance computation.
- **Reverse geocoding** — converts raw coordinates into usable start and end locations for both routing engines.

## Application Features

### Multi-Objective Optimization

A weight slider (0–1) lets the user set their own balance between two objectives:

- **CO2 priority** — a higher weighting on emissions favors public transport.
- **Time priority** — a lower weighting on emissions shifts the recommendation toward faster options, typically car travel.

### Comparative Analytics

For each trip, the app surfaces the underlying trade-off rather than hiding it behind a single recommendation:

- **Time and emissions side by side** — e.g., 21 minutes by car versus 65 minutes by public transport, against 1.2 kg versus 0.3 kg of CO2.
- **Weighted scoring** — a single score, computed from the user's chosen weighting, where a lower score indicates the better match to that user's stated priorities.
- **Impact visualization** — the CO2 savings of choosing public transport are shown directly against the time cost of doing so, making the trade-off legible at a glance.

## Conclusion

OTPORSApp combines containerized, modular routing infrastructure with a user-centric weighting model to show how technical tooling can support sustainable behavioral shifts in everyday mobility decisions.
