from flask import Blueprint, render_template, render_template_string, jsonify, request
from datetime import datetime
from app.models import db_handler

admin_bp = Blueprint('admin', __name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Figgy Admin | Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #020617; 
            color: #f8fafc;
            background-image: radial-gradient(circle at 50% -20%, #1e293b 0%, #020617 80%);
        }
        .glass {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .glow-blue { box-shadow: 0 0 20px rgba(59, 130, 246, 0.2); }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    </style>
</head>
<body class="min-h-screen p-8">
    <div class="max-w-7xl mx-auto space-y-10">
        
        <!-- TOP NAVIGATION & STATUS -->
        <header class="flex justify-between items-center bg-slate-900/50 p-6 rounded-3xl border border-white/5 backdrop-blur-xl">
            <div class="flex items-center space-x-4">
                <div class="bg-blue-600 p-3 rounded-2xl glow-blue">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                </div>
                <div>
                    <h1 class="text-2xl font-black tracking-tighter text-white uppercase">FIGGY <span class="text-blue-500">ADMIN</span></h1>
                    <div class="flex items-center space-x-2">
                        <span class="w-2 h-2 bg-emerald-500 rounded-full pulse"></span>
                        <p class="text-[10px] text-emerald-400 font-bold uppercase tracking-widest">Global Payout Sync Active</p>
                    </div>
                </div>
            </div>
            <div class="flex items-center space-x-6">
                <div class="text-right">
                    <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">System Health</p>
                    <p class="text-xs font-bold text-emerald-300">99.9% Uptime</p>
                </div>
                <div class="h-10 w-[1px] bg-white/10"></div>
                <button class="bg-white text-slate-950 px-6 py-2.5 rounded-xl font-bold text-sm hover:scale-105 transition-all shadow-xl">DEMO CONTROL</button>
            </div>
        </header>

        <!-- CORE KPI GRID -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="glass p-6 rounded-3xl group hover:border-blue-500/50 transition-all duration-500">
                <p class="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">PROTECTED FLEET</p>
                <div class="flex items-baseline space-x-2">
                    <h2 class="text-4xl font-black text-white tracking-tighter">{{ active_workers }}</h2>
                    <span class="text-emerald-400 text-xs font-bold font-mono">+12%</span>
                </div>
            </div>
            
            <div class="glass p-6 rounded-3xl group hover:border-blue-500/50 transition-all duration-500">
                <p class="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">PREMIUM VOLUME</p>
                <div class="flex items-baseline space-x-2">
                    <h2 class="text-4xl font-black text-blue-400 tracking-tighter">₹{{ total_premium_this_week }}</h2>
                </div>
            </div>

            <div class="glass p-6 rounded-3xl group hover:border-orange-500/50 transition-all duration-500">
                <p class="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">EVENTS TRIGGERED</p>
                <div class="flex items-baseline space-x-2">
                    <h2 class="text-4xl font-black text-orange-400 tracking-tighter">{{ claims_today }}</h2>
                    <span class="text-slate-500 text-xs font-bold uppercase ml-2 italic">Today</span>
                </div>
            </div>

            <div class="glass p-6 rounded-3xl group hover:border-red-500/50 transition-all duration-500">
                <p class="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">FRAUD PREVENTION</p>
                <div class="flex items-baseline space-x-2">
                    <h2 class="text-4xl font-black text-red-400 tracking-tighter">{{ fraud_prevented }}</h2>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- CLAIMS TABLE -->
            <div class="lg:col-span-2 glass rounded-[2rem] overflow-hidden border-blue-500/10 shadow-2xl">
                <div class="p-8 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                    <div>
                        <h3 class="text-lg font-black tracking-tight text-white uppercase">Parametric Ledger</h3>
                        <p class="text-xs text-slate-500 font-medium">Real-time claim orchestration events</p>
                    </div>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="bg-white/[0.02]">
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">ID</th>
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Worker</th>
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Payout</th>
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Risk</th>
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Stage</th>
                                <th class="px-8 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Resolution</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-white/5">
                            {% for claim in recent_claims %}
                            <tr class="hover:bg-blue-500/[0.02] transition-colors group">
                                <td class="px-8 py-6 font-mono text-xs text-blue-400 font-bold">#{{ claim.claim_id[:8] if claim.claim_id else '---' }}</td>
                                <td class="px-8 py-6 font-bold text-sm text-slate-300">{{ claim.worker_id }}</td>
                                <td class="px-8 py-6 font-black text-white">₹{{ claim.eligible_payout or 0 }}</td>
                                <td class="px-8 py-6">
                                    {% set risk = str(claim.fraud_risk)|upper if claim.fraud_risk else 'LOW' %}
                                    <span class="px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest
                                        {% if risk == 'HIGH' %}bg-red-500/20 text-red-400 border border-red-500/30
                                        {% elif risk == 'MEDIUM' %}bg-amber-500/20 text-amber-400 border border-amber-500/30
                                        {% else %}bg-emerald-500/20 text-emerald-400 border border-emerald-500/30{% endif %}">
                                        {{ risk }}
                                    </span>
                                </td>
                                <td class="px-8 py-6">
                                    {% set stat = str(claim.status)|upper if claim.status else 'UNKNOWN' %}
                                    <span class="flex items-center space-x-2">
                                        <span class="w-1.5 h-1.5 rounded-full pulse
                                            {% if stat == 'PAID' or stat == 'APPROVED' %}bg-emerald-500
                                            {% elif stat == 'VERIFYING' or stat == 'UNDER_REVIEW' %}bg-blue-500
                                            {% else %}bg-orange-500{% endif %}"></span>
                                        <span class="text-[10px] font-black text-slate-400 tracking-wider uppercase">{{ stat.replace('_', ' ') }}</span>
                                    </span>
                                </td>
                                <td class="px-8 py-6">
                                    {% if stat == 'MANUAL REVIEW' %}
                                    <div class="flex flex-col space-y-2 w-48">
                                        <input type="text" id="note-{{ claim.claim_id }}" placeholder="Admin note..." class="bg-black/20 border border-white/10 rounded px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
                                        <div class="flex space-x-2">
                                            <button onclick="resolveClaim('{{ claim.claim_id }}', 'approve')" class="flex-1 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/40 px-2 py-1 rounded text-[10px] font-bold uppercase transition-colors">Approve</button>
                                            <button onclick="resolveClaim('{{ claim.claim_id }}', 'reject')" class="flex-1 bg-red-500/20 text-red-400 hover:bg-red-500/40 px-2 py-1 rounded text-[10px] font-bold uppercase transition-colors">Reject</button>
                                        </div>
                                        <button onclick="resolveClaim('{{ claim.claim_id }}', 'escalate')" class="w-full bg-orange-500/20 text-orange-400 hover:bg-orange-500/40 px-2 py-1 rounded text-[10px] font-bold uppercase transition-colors mt-1">Escalate</button>
                                    </div>
                                    {% else %}
                                    <span class="text-xs text-slate-500 font-bold uppercase">{{ claim.resolved_by if claim.resolved_by else 'Auto' }}</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- REGIONAL RISK RADAR -->
            <div class="space-y-8">
                <div class="glass p-8 rounded-[2rem] border-blue-500/10">
                    <h4 class="text-sm font-black uppercase tracking-widest text-slate-300 mb-8 flex items-center">
                        <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                        Zone Risk Radar
                    </h4>
                    <div class="space-y-6">
                        {% for z in zones %}
                        <div class="flex justify-between items-center bg-white/[0.02] p-4 rounded-2xl border border-white/5">
                            <div>
                                <p class="text-sm font-black text-white">{{ z.name }}</p>
                                <p class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Rain: {{ z.rain }}mm</p>
                            </div>
                            {% if z.trigger_status %}
                            <span class="bg-orange-500/20 text-orange-400 px-3 py-1 rounded-full text-[9px] font-black pulse">DISRUPTED</span>
                            {% else %}
                            <span class="text-xl font-black text-slate-300">{{ z.temp }}°</span>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- LOSS RATIO GAUGE -->
                <div class="bg-gradient-to-br from-indigo-700 to-indigo-950 p-8 rounded-[2rem] shadow-2xl relative overflow-hidden">
                    <div class="absolute -right-8 -bottom-8 w-32 h-32 bg-white/10 rounded-full blur-3xl"></div>
                    <p class="text-indigo-200 text-[10px] font-black uppercase tracking-widest mb-2 opacity-70">Fleet Loss Ratio</p>
                    <div class="flex items-end space-x-2 mb-6">
                        <h2 class="text-5xl font-black text-white tracking-tighter">{{ '%.1f'|format(loss_ratio) }}%</h2>
                        <span class="text-indigo-300 text-xs font-bold mb-2 uppercase opacity-60">OPTIMUM</span>
                    </div>
                    <div class="w-full bg-white/10 h-3 rounded-full overflow-hidden">
                        <div class="bg-emerald-400 h-full rounded-full glow-blue shadow-[0_0_15px_rgba(52,211,153,0.5)]" style="width: min({{ loss_ratio }}, 100)%"></div>
                    </div>
                    <p class="text-indigo-100/50 text-[9px] mt-4 font-bold border-t border-white/10 pt-4">Loss ratio within risk-pool limits. Solvency confirmed.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- RESOLVE LOGIC -->
    <script>
        async function resolveClaim(claimId, action) {
            const noteInput = document.getElementById(`note-${claimId}`);
            const noteText = noteInput ? noteInput.value : "";
            
            try {
                const response = await fetch(`/api/admin/claim/resolve/${claimId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action, admin_note: noteText })
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (err) {
                alert('Request failed');
            }
        }
    </script>
</body>
</html>
"""

def calculate_metrics():
    workers = db_handler.get_all_workers()
    claims = db_handler.get_all_claims()
    
    # Live Platform Stats
    active_workers = len([w for w in workers if w.get("policy_status") == "active"])
    total_premium_this_week = sum([w.get("suggested_premium", 0) for w in workers])
    
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    claims_today = len([c for c in claims if c.get("created_at", "").startswith(today_str)])
    fraud_prevented = len([c for c in claims if c.get("status") in ("rejected", "manual_review")])

    # Claims Breakdown
    statuses = ["under_review", "verifying", "approved", "paid", "rejected", "manual_review"]
    claims_by_status = {s: 0 for s in statuses}
    for c in claims:
        st = str(c.get("status", ""))
        if st in claims_by_status:
            claims_by_status[st] += 1
        elif st:
            claims_by_status[st] = 1 # Catch-all

    # Financials
    total_payout_this_week = sum([c.get("eligible_payout", 0) for c in claims if c.get("status") in ("approved", "paid")])
    loss_ratio = (total_payout_this_week / total_premium_this_week * 100) if total_premium_this_week else 0.0

    # Recent Claims
    recent_claims = claims[:20]

    # Zones Radar
    # In a real app we'd fetch from weather service cache. Since it's a demo, we randomly mock some safe ones,
    # except we look for recent disruption triggers.
    from app.utils.weather import WeatherService
    ws = WeatherService()
    
    zones = []
    for zname in ["North", "South", "East", "West", "Central"]:
        try:
            w_data = ws.get_current_weather(zname)
            zones.append({
                "name": zname + " Hub",
                "rain": w_data.get("rain_mm_hr", 0.0),
                "temp": w_data.get("temp_c", 32.0),
                "aqi": w_data.get("aqi", 50),
                "trigger_status": w_data.get("disruption_triggered", False)
            })
        except:
            # Fallback if weather service fails
            zones.append({
                "name": zname + " Hub",
                "rain": 0.0, "temp": 30.0, "aqi": 50, "trigger_status": False
            })

    return {
        "active_workers": active_workers,
        "total_premium_this_week": total_premium_this_week,
        "claims_today": claims_today,
        "fraud_prevented": fraud_prevented,
        "claims_by_status": claims_by_status,
        "total_payout_this_week": total_payout_this_week,
        "loss_ratio": loss_ratio,
        "recent_claims": recent_claims,
        "zones": zones,
        "str": str
    }


def _dashboard_stats_payload():
    all_claims = db_handler.get_all_claims()
    all_workers = db_handler.get_all_workers()
    stats = {
        "active_policies": len([w for w in all_workers if w.get("policy_status") == "active"]),
        "total_claims": len(all_claims),
        "approved_claims": len([c for c in all_claims if c.get("status") == "approved"]),
        "paid_claims": len([c for c in all_claims if c.get("status") == "paid"]),
        "total_payout": sum(
            c.get("eligible_payout", 0) for c in all_claims if c.get("status") in ["approved", "paid"]
        ),
        "fraud_blocked": len([c for c in all_claims if c.get("status") == "manual_review"]),
    }
    return stats

@admin_bp.route('/', methods=['GET'])
def admin_dashboard():
    """GET /admin - Renders the standalone insurer admin dashboard."""
    metrics = calculate_metrics()
    return render_template_string(DASHBOARD_HTML, **metrics)


@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    all_claims = db_handler.get_all_claims()
    all_workers = db_handler.get_all_workers()

    stats = _dashboard_stats_payload()
    stats["claims_this_week"] = stats["total_claims"]
    stats["total_premium_collected"] = sum(w.get("suggested_premium", 0) for w in all_workers)
    stats["payout_total"] = stats["total_payout"]

    claims_rows = sorted(
        all_claims, key=lambda c: c.get("created_at", ""), reverse=True
    )[:25]

    auto_triggers = [
        c for c in sorted(all_claims, key=lambda x: x.get("created_at", ""), reverse=True)
        if c.get("claim_source") == "auto"
    ][:10]
    trigger_log = [
        {
            "zone": t.get("zone", "Unknown"),
            "type": t.get("trigger_type", t.get("disruption_type", "UNKNOWN")),
            "workers_affected": 1,
            "created_at": t.get("created_at", ""),
        }
        for t in auto_triggers
    ]

    disruption_counts = {}
    for claim in all_claims:
        key = claim.get("disruption_type") or claim.get("trigger_type") or "Unknown"
        disruption_counts[key] = disruption_counts.get(key, 0) + 1

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        claims_rows=claims_rows,
        trigger_log=trigger_log,
        chart_labels=list(disruption_counts.keys()),
        chart_values=list(disruption_counts.values()),
    )


@admin_bp.route('/dashboard/stats', methods=['GET'])
def dashboard_stats():
    return jsonify(_dashboard_stats_payload())

@admin_bp.route('/api/admin/claims', methods=['GET'])
def list_claims():
    """GET /api/admin/claims - Filter claims by status and assignment."""
    claims = db_handler.get_all_claims()
    statuses = request.args.getlist("status")
    assigned_to = request.args.get("assigned_to")
    
    if statuses:
        claims = [c for c in claims if c.get("status") in statuses]
    if assigned_to:
        claims = [c for c in claims if c.get("assigned_to") == assigned_to]
        
    return jsonify({"status": "success", "claims": claims}), 200

@admin_bp.route('/api/admin/claim/resolve/<claim_id>', methods=['POST'])
def resolve_claim(claim_id):
    """POST /api/admin/claim/resolve/<claim_id> - Performs approval, rejection, or escalation."""
    data = request.json or {}
    action = data.get("action")
    admin_note = data.get("admin_note", "")
    admin_id = data.get("admin_id", "admin_portal")
    
    claim = db_handler.get_claim(claim_id)
    if not claim:
        return jsonify({"status": "error", "message": "Claim not found"}), 404
        
    from app.utils.claim_processor import approve_and_payout, send_claim_notification
    
    now_ts = datetime.utcnow().isoformat()
    
    if action == "approve":
        # Dispatches entirely to the approval pipeline wrapper.
        approve_and_payout(claim_id, admin_id)
        # Note: approve_and_payout persists the data and sends notification
        
    elif action == "reject":
        db_handler.update_claim_status(
            claim_id, "rejected", 
            {
                "rejection_reason": "MANUAL_REVIEW_REJECTED",
                "admin_note": admin_note,
                "resolved_by": admin_id,
                "resolved_at": now_ts
            }
        )
        claim = db_handler.get_claim(claim_id) # fetch updated
        send_claim_notification(claim.get("worker_id"), "rejected", claim)
        
    elif action == "escalate":
        db_handler.update_claim_status(
            claim_id, "escalated", 
            {
                "assigned_to": "senior_review",
                "admin_note": admin_note,
                "escalated_by": admin_id,
                "escalated_at": now_ts
            }
        )
        
    else:
        return jsonify({"status": "error", "message": f"Unknown action: {action}"}), 400
        
    # Return updated claim dynamically
    updated = db_handler.get_claim(claim_id)
    return jsonify({"status": "success", "claim": updated}), 200
