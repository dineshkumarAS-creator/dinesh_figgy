# Figgy GigShield — Demo Checklist

This is the official pre-flight checklist and presentation script for the hackathon. Run through these exact steps 1 hour prior to presenting to ensure zero surprises.

## Pre-demo checks (run 1 hour before)
- [ ] Flask server starts without errors (`python run.py`)
- [ ] `GET http://localhost:5000/health` returns 200 OK
- [ ] Worker GS-OVVSRL has policy_status=active (Verify in logs or database)
- [ ] `/admin` dashboard loads at `http://localhost:5000/admin` and safely shows data without crashing
- [ ] OpenWeatherMap API key (and Razorpay keys) are set OR `MOCK MODE` is confirmed working in the terminal logs
- [ ] `POST http://localhost:5000/api/demo/trigger_rain` smoothly creates a mock claim
- [ ] Flutter app runs successfully (`flutter run -d chrome --web-port=8080`)
- [ ] **Radar Screen** shows live weather data cleanly (not blank/loading indefinitely)
- [ ] **Insurance Screen** correctly loads the active claims list history
- [ ] Submitted **Manual Claim** properly fires the processing UI and propagates a new entry to the `claim_details` view

---

## 5-Minute Demo Script
Stick strictly to this chronological timeline to guarantee the narrative lands safely:

**Min 0-1:**
Show **Ravi's Profile** — Point out he is successfully enrolled with an active **"Smart"** Policy, showing coverage up to ₹500/disruption.

**Min 1-2:**
Show the **Radar Screen** — Inform the judges that the area is currently clear (0.0mm/hr rainfall).
*Hit the "SIMULATE RAIN (DEMO)" debug button at the bottom of the screen.* Keep eyes on the screen as the alert appears immediately.

**Min 2-3:**
Transition smoothly over to the **Insurance Tab**. Point to the newly created mock claim. Keep talking for 5-10 seconds to allow the internal real-time polling to silently switch the claim status to `"Verifying"` and then `"Approved/Paid"`. 

**Min 3-4:**
Once it flips to `Paid`, open up the **Claim Details**. Show the breakdown of the Rs. 400 total payout. Emphasize that all this math occurred precisely and completely autonomously with zero interaction from Ravi.

**Min 4-5:**
End on a high note by swapping over to the web browser and pulling up **`http://localhost:5000/admin`**. 
Highlight the live platform metrics, calculating loss ratio securely while displaying recent prevented fraud on the underlying orchestrator.
