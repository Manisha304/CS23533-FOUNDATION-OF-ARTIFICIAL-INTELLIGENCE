/**
 * stadium_twin/static/js/dashboard.js
 * ===================================
 * Chepauk Stadium Interactive Canvas Visualizer & Real-Time API Polling.
 */

document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("stadium-canvas");
    const ctx = canvas.getContext("2d");

    let currentState = null;
    let particles = [];
    let particlesEnabled = true;

    // Chepauk 1000x800 canvas node coordinates
    const spatialPosMap = {
        "Gate_1_Wallajah":   { x: 500, y: 70 },
        "Gate_2_Bells":      { x: 910, y: 360 },
        "Gate_3_Pattabiram": { x: 500, y: 730 },
        "Gate_4_Vattaram":   { x: 120, y: 360 },
        "Concourse_North":   { x: 500, y: 130 },
        "Concourse_South":   { x: 500, y: 650 },
        "Junction_West":     { x: 200, y: 360 },
        "Junction_East":     { x: 810, y: 360 },
        "Anna_Pavilion":        { x: 500, y: 190 },
        "Pavilion_Stand":       { x: 500, y: 590 },
        "P4_Upper_Stand":       { x: 720, y: 360 },
        "CD_Stand":             { x: 280, y: 360 },
        "MA_Chidambaram_Stand": { x: 500, y: 270 },
        "Parking_Area":   { x: 80,  y: 680 },
        "Emergency_Exit": { x: 860, y: 80 }
    };

    const COLOR_OK = "#2ecc71";
    const COLOR_WARNING = "#f1c40f";
    const COLOR_OVERLOADED = "#e74c3c";
    const COLOR_BLOCKED = "#64748b";
    const COLOR_EMERGENCY = "#9b59b6";
    const COLOR_EDGE = "#334155";
    const COLOR_REROUTE_EDGE = "#2563eb";

    function updateClock() {
        const now = new Date();
        document.getElementById("live-clock").textContent = now.toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    async function fetchState() {
        try {
            const response = await fetch("/api/state");
            const data = await response.json();
            currentState = data;
            updateDashboardUI(data);
        } catch (err) {
            console.error("Error fetching state:", err);
        }
    }

    async function setScenario(scenarioName) {
        try {
            await fetch("/api/scenario", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario: scenarioName })
            });
            fetchState();
        } catch (err) {
            console.error("Error setting scenario:", err);
        }
    }

    async function toggleBlockNode(nodeId) {
        try {
            await fetch("/api/node/toggle-block", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ node: nodeId })
            });
            fetchState();
        } catch (err) {
            console.error("Error toggling block:", err);
        }
    }

    async function triggerEmergency(nodeId) {
        try {
            await fetch("/api/emergency", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ node: nodeId, severity: 5, description: `Level 5 Fire Hazard at ${nodeId}` })
            });
            fetchState();
        } catch (err) {
            console.error("Error triggering emergency:", err);
        }
    }

    async function clearEmergencies() {
        try {
            await fetch("/api/clear-emergencies", { method: "POST" });
            fetchState();
        } catch (err) {
            console.error("Error clearing emergencies:", err);
        }
    }

    // --- Controls Listeners ---
    document.querySelectorAll(".btn-scenario").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".btn-scenario").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const scenario = btn.getAttribute("data-scenario");
            setScenario(scenario);
        });
    });

    document.getElementById("btn-toggle-block").addEventListener("click", () => {
        const node = document.getElementById("select-node").value;
        toggleBlockNode(node);
    });

    document.getElementById("btn-trigger-emergency").addEventListener("click", () => {
        const node = document.getElementById("select-node").value;
        triggerEmergency(node);
    });

    document.getElementById("btn-clear-emergencies").addEventListener("click", () => {
        clearEmergencies();
    });

    document.getElementById("btn-toggle-particles").addEventListener("click", (e) => {
        particlesEnabled = !particlesEnabled;
        e.target.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Particles: ${particlesEnabled ? 'ON' : 'OFF'}`;
    });

    function updateDashboardUI(data) {
        const actionPlan = data.action_plan;
        const kpis = data.kpis;

        // 1. Status Badge
        const badge = document.getElementById("system-status-badge");
        const statusText = document.getElementById("status-text");

        badge.className = "status-indicator-badge";
        if (actionPlan.status === "EVACUATION") {
            badge.classList.add("status-evacuation");
            statusText.textContent = "CRITICAL EVACUATION";
        } else if (actionPlan.status === "REROUTE") {
            badge.classList.add("status-reroute");
            statusText.textContent = "CONGESTION DIVERSION";
        } else {
            badge.classList.add("status-monitoring");
            statusText.textContent = "MONITORING NORMAL";
        }

        // 2. KPI Cards
        document.getElementById("kpi-total-load").textContent = `${kpis.total_load.toLocaleString()} / ${kpis.total_capacity.toLocaleString()}`;
        document.getElementById("kpi-total-pct").textContent = `${kpis.overall_occupancy_pct}% Capacity`;

        document.getElementById("kpi-peak-node").textContent = kpis.peak_node;
        document.getElementById("kpi-peak-pct").textContent = `${kpis.peak_node_pct}% Capacity Load`;

        document.getElementById("kpi-target-node").textContent = actionPlan.target_node;
        if (kpis.active_emergency && kpis.emergency_details) {
            document.getElementById("kpi-emergency-status").textContent = `Fire Hazard at ${kpis.emergency_details.node} (Sev 5)`;
        } else {
            document.getElementById("kpi-emergency-status").textContent = "No Active Hazard";
        }

        // 3. Gate Breakdown List
        const gateListContainer = document.getElementById("gate-metrics-list");
        gateListContainer.innerHTML = "";
        const gates = ["Gate_1_Wallajah", "Gate_2_Bells", "Gate_3_Pattabiram", "Gate_4_Vattaram"];

        gates.forEach(g => {
            const gData = data.graph_state.nodes[g];
            if (!gData) return;

            const pct = Math.round(gData.load_factor * 100);
            let barColor = COLOR_OK;
            if (gData.blocked) barColor = COLOR_BLOCKED;
            else if (pct >= 90) barColor = COLOR_OVERLOADED;
            else if (pct >= 70) barColor = COLOR_WARNING;

            const itemHTML = `
                <div class="gate-metric-item">
                    <div class="gate-metric-header">
                        <span>${gData.label || g} ${gData.blocked ? '(BLOCKED)' : ''}</span>
                        <span>${gData.current_load} / ${gData.capacity} (${pct}%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${pct}%; background-color: ${barColor};"></div>
                    </div>
                </div>
            `;
            gateListContainer.insertAdjacentHTML("beforeend", itemHTML);
        });

        // 4. Terminal Logs
        const terminal = document.getElementById("terminal-body");
        terminal.innerHTML = "";

        actionPlan.decision_trace.forEach(line => {
            let cssClass = "log-line";
            if (line.includes("[Crowd Agent]")) cssClass += " log-crowd";
            else if (line.includes("[Route Agent]")) cssClass += " log-route";
            else if (line.includes("[Safety Agent]")) cssClass += " log-safety";
            else if (line.includes("[Coordinator]")) cssClass += " log-coordinator";

            const p = document.createElement("div");
            p.className = cssClass;
            p.textContent = line;
            terminal.appendChild(p);
        });
        terminal.scrollTop = terminal.scrollHeight;

        // 5. Action Summary Box
        document.getElementById("action-message").textContent = actionPlan.message;
        const pathsList = document.getElementById("reroute-paths-list");
        pathsList.innerHTML = "";

        if (actionPlan.reroute_paths) {
            Object.entries(actionPlan.reroute_paths).forEach(([origin, path]) => {
                if (Array.isArray(path) && path.length > 1) {
                    const li = document.createElement("li");
                    li.textContent = `${origin} ➔ ${path.join(" ➔ ")}`;
                    pathsList.appendChild(li);
                }
            });
        }

        if (particlesEnabled && actionPlan.reroute_paths) {
            spawnCrowdParticles(actionPlan.reroute_paths);
        }
    }

    function spawnCrowdParticles(reroutePaths) {
        Object.values(reroutePaths).forEach(path => {
            if (Array.isArray(path) && path.length > 1) {
                for (let i = 0; i < 2; i++) {
                    particles.push({
                        path: path,
                        pathIndex: 0,
                        progress: Math.random(),
                        speed: 0.006 + Math.random() * 0.004,
                        size: 3 + Math.random() * 2
                    });
                }
            }
        });
        if (particles.length > 150) particles = particles.slice(-150);
    }

    function updateAndDrawParticles() {
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.progress += p.speed;

            if (p.progress >= 1.0) {
                p.progress = 0.0;
                p.pathIndex++;
                if (p.pathIndex >= p.path.length - 1) {
                    particles.splice(i, 1);
                    continue;
                }
            }

            const fromNode = p.path[p.pathIndex];
            const toNode = p.path[p.pathIndex + 1];

            const fromPos = spatialPosMap[fromNode];
            const toPos = spatialPosMap[toNode];

            if (fromPos && toPos) {
                const curX = fromPos.x + (toPos.x - fromPos.x) * p.progress;
                const curY = fromPos.y + (toPos.y - fromPos.y) * p.progress;

                ctx.beginPath();
                ctx.arc(curX, curY, p.size, 0, Math.PI * 2);
                ctx.fillStyle = "#38bdf8";
                ctx.shadowColor = "#38bdf8";
                ctx.shadowBlur = 8;
                ctx.fill();
                ctx.shadowBlur = 0;
            }
        }
    }

    // --- Canvas Drawing Loop ---
    function renderCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!currentState) {
            requestAnimationFrame(renderCanvas);
            return;
        }

        const nodes = currentState.graph_state.nodes;
        const edges = currentState.graph_state.edges;
        const actionPlan = currentState.action_plan;
        const emergencyNode = actionPlan.emergency_node;

        const rerouteEdgeSet = new Set();
        if (actionPlan.reroute_paths) {
            Object.values(actionPlan.reroute_paths).forEach(path => {
                if (Array.isArray(path) && path.length > 1) {
                    for (let i = 0; i < path.length - 1; i++) {
                        rerouteEdgeSet.add(`${path[i]}--${path[i+1]}`);
                        rerouteEdgeSet.add(`${path[i+1]}--${path[i]}`);
                    }
                }
            });
        }

        // 1. Draw Walkway Edges
        edges.forEach(([u, v, w]) => {
            const p1 = spatialPosMap[u];
            const p2 = spatialPosMap[v];
            if (!p1 || !p2) return;

            const isReroute = rerouteEdgeSet.has(`${u}--${v}`);

            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);

            if (isReroute) {
                ctx.strokeStyle = COLOR_REROUTE_EDGE;
                ctx.lineWidth = 5;
                ctx.shadowColor = COLOR_REROUTE_EDGE;
                ctx.shadowBlur = 12;
            } else {
                ctx.strokeStyle = COLOR_EDGE;
                ctx.lineWidth = 3;
                ctx.shadowBlur = 0;
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
        });

        // 2. Draw Chepauk Outer Ellipse Boundary
        ctx.beginPath();
        ctx.ellipse(500, 400, 350, 300, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "#1e293b";
        ctx.lineWidth = 4;
        ctx.stroke();

        // 3. Draw Center Cricket Pitch Ground
        ctx.beginPath();
        ctx.ellipse(500, 400, 140, 160, 0, 0, Math.PI * 2);
        ctx.fillStyle = "#228b22";
        ctx.fill();
        ctx.strokeStyle = "#2eea67";
        ctx.lineWidth = 3;
        ctx.stroke();

        // 30-yard boundary line
        ctx.beginPath();
        ctx.ellipse(500, 400, 110, 130, 0, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Pitch turf crease rectangle
        ctx.fillStyle = "#c2a878";
        ctx.fillRect(485, 360, 30, 80);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(485, 360, 30, 80);

        // 4. Draw Parking Lot (West Exterior)
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(30, 620, 120, 120);
        ctx.strokeStyle = "#475569";
        ctx.lineWidth = 2;
        ctx.strokeRect(30, 620, 120, 120);

        ctx.fillStyle = "#94a3b8";
        ctx.font = "bold 11px Outfit, sans-serif";
        ctx.fillText("PARKING LOT", 50, 640);
        
        [650, 675, 700].forEach(y => {
            [45, 80, 115].forEach(x => {
                ctx.fillStyle = "#64748b";
                ctx.fillRect(x, y, 16, 10);
            });
        });

        // 5. Draw Emergency Safety Exit (North-East Box)
        ctx.fillStyle = "#e74c3c";
        ctx.fillRect(810, 60, 110, 45);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.strokeRect(810, 60, 110, 45);

        ctx.fillStyle = "#ffffff";
        ctx.fillRect(815, 72, 100, 20);
        ctx.fillStyle = "#000000";
        ctx.font = "bold 10px Outfit, sans-serif";
        ctx.fillText("EMERGENCY EXIT", 820, 86);

        // 6. Draw Moving Crowd Particles
        if (particlesEnabled) {
            updateAndDrawParticles();
        }

        // 7. Draw Graph Nodes (Stands and Gates)
        Object.entries(nodes).forEach(([nodeId, data]) => {
            const pos = spatialPosMap[nodeId];
            if (!pos) return;

            const isBlocked = data.blocked;
            const isEmergency = (nodeId === emergencyNode);
            const loadFactor = data.load_factor;
            const pct = Math.round(loadFactor * 100);

            let fillColor = COLOR_OK;
            if (isEmergency) fillColor = COLOR_EMERGENCY;
            else if (isBlocked) fillColor = COLOR_BLOCKED;
            else if (loadFactor >= 0.90) fillColor = COLOR_OVERLOADED;
            else if (loadFactor >= 0.70) fillColor = COLOR_WARNING;

            if (data.type === "stand") {
                ctx.fillStyle = "#0f172a";
                ctx.fillRect(pos.x - 70, pos.y - 30, 140, 60);
                ctx.strokeStyle = fillColor;
                ctx.lineWidth = 3;
                ctx.strokeRect(pos.x - 70, pos.y - 30, 140, 60);

                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 11px Outfit, sans-serif";
                ctx.textAlign = "center";
                ctx.fillText(data.label || nodeId, pos.x, pos.y - 6);

                ctx.fillStyle = fillColor;
                ctx.font = "bold 11px monospace";
                ctx.fillText(`Load: ${pct}%`, pos.x, pos.y + 12);
            } else if (data.type === "gate") {
                ctx.fillStyle = "#0f172a";
                ctx.fillRect(pos.x - 55, pos.y - 25, 110, 50);
                ctx.strokeStyle = fillColor;
                ctx.lineWidth = 3;
                ctx.strokeRect(pos.x - 55, pos.y - 25, 110, 50);

                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 10px Outfit, sans-serif";
                ctx.textAlign = "center";
                ctx.fillText(data.label || nodeId, pos.x, pos.y - 6);

                ctx.fillStyle = fillColor;
                ctx.font = "bold 10px monospace";
                ctx.fillText(`${pct}% ${isBlocked ? '(BLOCKED)' : ''}`, pos.x, pos.y + 10);
            }
        });

        requestAnimationFrame(renderCanvas);
    }

    fetchState();
    setInterval(fetchState, 1000);
    requestAnimationFrame(renderCanvas);
});
