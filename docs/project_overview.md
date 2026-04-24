# Figgy GigShield - Project Overview

## Introduction
Figgy GigShield is a parametric micro-insurance platform built specifically for delivery gig workers in India (Zomato, Swiggy, Zepto, etc.). It provides instant financial protection against involuntary income loss caused by external disruptions such as severe weather, floods, extreme heat, or strikes.

## Value Proposition
Gig workers face daily uncertainties. A traditional insurance model takes weeks to process a claim and requires manual adjustments. Figgy GigShield uses **parametric triggers** (e.g., rainfall > 40mm/hr) integrated with **Proof-of-Work (PoW)** telemetry to automatically initiate, verify, and disburse payouts within minutes, without human intervention.

## Core Architecture
The platform is built on a modern, decoupled tech stack designed for speed, scale, and high accessibility:

1. **Frontend (Flutter)**
   - Deployed as an Android App and a Web App.
   - Designed with an ultra-premium, dark-themed UI pattern tailored to high usability in outdoor environments.
   - Core tabs: Radar (live weather), Home (summary), Insurance (active policies & claims), Profile.

2. **Backend (Python / Flask)**
   - Houses the business logic, REST APIs, and background job orchestration.
   - State management is currently supported by an in-memory database and MongoDB.

3. **Background Jobs (APScheduler)**
   - Periodically polls third-party APIs (OpenWeather) to autonomously trigger claims for active workers in disrupted zones.

4. **Integration Layer**
   - **Razorpay Subscriptions**: Collects micro-premiums automatically.
   - **Razorpay Payouts (X)**: Sends instant UPI transfers to workers upon claim approval.
   - **Firebase Cloud Messaging (FCM)**: Delivers real-time push notifications about active claims and payouts.

## Target Audience & Tiers
Workers can subscribe to one of three tiers based on their daily earning averages:
- **Lite (₹29/week)**: Covers basic rain disruptions. Up to ₹300 max payout.
- **Smart (₹49/week)**: Covers rain, heat, and strikes. Up to ₹500 max payout.
- **Elite (₹89/week)**: Premium coverage, highest payouts (up to ₹750), includes surge bonuses.

## Hackathon / Demo Mode
The system features a robust "Demo Mode" fallback mechanism allowing judges and testers to fully evaluate the product end-to-end without real financial transactions, including simulated Razorpay payout hooks and controlled failure states.
