/**
 * AURELIA // SYSTEM STATUS ENGINE
 * Tracks the user's specific daily protocol and updates the UI.
 * * LOGIC MAP:
 * - KINETIC_OPS:     Lifting / Running / Drills (Orange)
 * - COMBAT_OPS:      Wrestling Practice (Green Pulse)
 * - NEURAL_UPLINK:   Classes (Purple)
 * - DEEP_WORK:       Study Hall / Desk Block (Green Pulse)
 * - SYSTEM_BOOT:     Wake up / Breakfast (Cyan)
 */

function updateSystemStatus() {
    const now = new Date();
    const day = now.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
    const hour = now.getHours();
    const min = now.getMinutes();
    const time = hour * 100 + min; // Convert 2:30pm to 1430 for easy comparison

    let status = "SYSTEM_IDLE";
    let color = "text-gray-500";
    let pulse = false;

    // --- MONDAY (1) / WEDNESDAY (3) / FRIDAY (5) ---
    // The Marathon Days
    if (day === 1 || day === 3 || day === 5) {
        
        // Wednesday Specific: Early Morning Run
        if (day === 3 && time >= 615 && time < 745) {
            status = "EARLY_GRIND // RUN";
            color = "text-aurelia-orange";
        }
        // Mon/Fri: Wake Up Phase
        else if (day !== 3 && time >= 715 && time < 800) {
            status = "SYSTEM_BOOT";
            color = "text-aurelia-cyan";
        }
        // Mon/Fri: Team Lift
        else if ((day === 1 || day === 5) && time >= 800 && time < 840) {
            status = "KINETIC_OPS // LIFT";
            color = "text-aurelia-orange";
        }
        // Academic Block (Classes)
        else if (time >= 900 && time < 1200) {
            status = "NEURAL_UPLINK // ACADEMIC";
            color = "text-aurelia-purple";
        }
        // Lunch / Recovery
        else if (time >= 1200 && time < 1300) {
            status = "FUELING_CYCLE";
            color = "text-gray-400";
        }
        // Afternoon Classes
        else if (time >= 1300 && time < 1400) {
            status = "NEURAL_UPLINK // ACADEMIC";
            color = "text-aurelia-purple";
        }
        // Pre-Practice Prep
        else if (time >= 1400 && time < 1500) {
            status = "PRE_COMBAT_PREP";
            color = "text-gray-400";
        }
        // WRESTLING PRACTICE (The Grind)
        else if (time >= 1500 && time < 1730) {
            status = "COMBAT_OPERATIONS // WRESTLING";
            color = "text-aurelia-green";
            pulse = true;
        }
        // Dinner / Shower
        else if (time >= 1730 && time < 1900) {
            status = "SYSTEM_MAINTENANCE";
            color = "text-gray-400";
        }
        // THE LOCK IN (Deep Work)
        else if (time >= 1900 && time < 2000) {
            status = "DEEP_WORK_PROTOCOL";
            color = "text-aurelia-green";
            pulse = true;
        }
        // Sleep
        else if (time >= 2300 || time < 615) {
            status = "SYSTEM_OFFLINE";
            color = "text-gray-700";
        }
        else {
            status = "SOCIAL_SYNC";
            color = "text-gray-400";
        }
    }

    // --- TUESDAY (2) / THURSDAY (4) ---
    // The Technical Days
    else if (day === 2 || day === 4) {
        if (time >= 715 && time < 930) {
            status = "SYSTEM_BOOT // REVIEW";
            color = "text-aurelia-cyan";
        }
        else if (time >= 930 && time < 1045) {
            status = "NEURAL_UPLINK";
            color = "text-aurelia-purple";
        }
        else if (time >= 1100 && time < 1145) {
            status = "KINETIC_OPS // DRILLS";
            color = "text-aurelia-orange";
        }
        else if (time >= 1200 && time < 1400) {
            status = "DEEP_WORK // STUDY_HALL";
            color = "text-aurelia-green";
        }
        else if (time >= 1500 && time < 1730) {
            status = "COMBAT_OPERATIONS // WRESTLING";
            color = "text-aurelia-green";
            pulse = true;
        }
        else if (time >= 1900 && time < 2000) {
            status = "DEEP_WORK_PROTOCOL";
            color = "text-aurelia-green";
            pulse = true;
        }
        else if (time >= 2300 || time < 715) {
            status = "SYSTEM_OFFLINE";
            color = "text-gray-700";
        }
        else {
            status = "SYSTEM_MAINTENANCE";
            color = "text-gray-400";
        }
    }

    // --- SATURDAY (6) ---
    // Growth & Recovery
    else if (day === 6) {
        if (time >= 830 && time < 1030) {
            status = "CREATIVE_BUILD // PROJECT";
            color = "text-aurelia-cyan";
            pulse = true;
        }
        else if (time >= 1030 && time < 1130) {
            status = "NEURAL_EXPANSION"; // Study
            color = "text-aurelia-green";
        }
        else if (time >= 1330 && time < 1730) {
            status = "RECHARGE_CYCLE"; // Strict Rest
            color = "text-gray-500";
        }
        else if (time >= 2300) {
            status = "SYSTEM_OFFLINE";
            color = "text-gray-700";
        }
        else {
            status = "SOCIAL_SYNC";
            color = "text-gray-400";
        }
    }

    // --- SUNDAY (0) ---
    // The Reset
    else if (day === 0) {
        if (time >= 930 && time < 1100) {
            status = "ADMIN_OVERRIDE // FINANCE";
            color = "text-aurelia-orange";
        }
        else if (time >= 1100 && time < 1300) {
            status = "LOGISTICS // RESUPPLY"; // Grocery
            color = "text-gray-400";
        }
        else if (time >= 1700 && time < 1900) {
            status = "LOGISTICS // MEAL_PREP";
            color = "text-aurelia-cyan";
        }
        else if (time >= 2300) {
            status = "SYSTEM_OFFLINE";
            color = "text-gray-700";
        }
        else {
            status = "SYSTEM_RESET";
            color = "text-gray-500";
        }
    }

    // --- UPDATE DOM ---
    const statusEl = document.getElementById('live-status-text');
    const indicatorEl = document.getElementById('live-status-indicator');
    
    if (statusEl) {
        statusEl.innerText = status;
        
        // Remove old color classes (rudimentary clear)
        statusEl.className = ""; 
        statusEl.classList.add("font-mono", "text-xs", "tracking-widest", color);
        
        // Handle the glowing dot
        // We replace 'text-' with 'bg-' for the dot
        const bgClass = color.replace('text-', 'bg-');
        indicatorEl.className = `w-2 h-2 rounded-full ${bgClass} ${pulse ? 'animate-pulse' : ''}`;
    }
}

// Initial Run
updateSystemStatus();

// Update every 60 seconds
setInterval(updateSystemStatus, 60000);