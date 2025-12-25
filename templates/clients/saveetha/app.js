// -------- Side Menu & Overlay --------
const hamburger = document.getElementById("hamburger");
const sideMenu = document.getElementById("sideMenu");

// create overlay in JS (optional, or you can hardcode it in HTML)
let overlay = document.getElementById("menuOverlay");
if (!overlay) {
  overlay = document.createElement("div");
  overlay.id = "menuOverlay";
  overlay.className = "menu-overlay hidden";
  document.body.appendChild(overlay);
}

// open/close when hamburger clicked
hamburger.onclick = function () {
  const isHidden = sideMenu.classList.contains("hidden");
  if (isHidden) {
    sideMenu.classList.remove("hidden");
    overlay.classList.remove("hidden");
  } else {
    sideMenu.classList.add("hidden");
    overlay.classList.add("hidden");
  }
};

// close when clicking overlay
overlay.addEventListener("click", () => {
  sideMenu.classList.add("hidden");
  overlay.classList.add("hidden");
});

// -------- Theme Toggle --------
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const compassLogo = document.querySelector(".corner-logo");

// Load saved theme on page load
if (localStorage.getItem("theme") === "dark") {
  document.body.classList.add("dark-theme");
  // UPDATED PATHS
  themeIcon.src = "/saveetha_files/assets/moon.jpg";
  compassLogo.src = "/saveetha_files/assets/compass-dark.svg";
} else {
  document.body.classList.remove("dark-theme");
  // UPDATED PATHS
  themeIcon.src = "/saveetha_files/assets/sun-removebg-preview.png";
  compassLogo.src = "/saveetha_files/assets/compass.svg";
}

// Toggle theme on click
themeToggle.addEventListener("click", () => {
  const isDark = document.body.classList.toggle("dark-theme");

  // UPDATED PATHS
  themeIcon.src = isDark ? "/saveetha_files/assets/moon.jpg" : "/saveetha_files/assets/sun-removebg-preview.png";

  // UPDATED PATHS
  compassLogo.src = isDark ? "/saveetha_files/assets/compass-dark.svg" : "/saveetha_files/assets/compass.svg"; 

  localStorage.setItem("theme", isDark ? "dark" : "light");
});





// ... (Your existing Side Menu & Theme Toggle code is above here) ...

// ==========================================
//        ALGORITHM CONNECTION (A*)
// ==========================================

const routeForm = document.getElementById('routeForm');
const errorMsg = document.getElementById('errorMsg');

// We need a place to show the results. 
// Let's create a result container dynamically if it doesn't exist.
let resultContainer = document.getElementById('resultContainer');
if (!resultContainer) {
    resultContainer = document.createElement('div');
    resultContainer.id = 'resultContainer';
    resultContainer.style.marginTop = '20px';
    resultContainer.style.padding = '20px';
    resultContainer.style.border = '3px solid black';
    resultContainer.style.display = 'none'; // Hidden by default
    
    // Insert it after the form
    routeForm.parentNode.insertBefore(resultContainer, routeForm.nextSibling);
}

// routeForm.addEventListener('submit', async (e) => {
//     e.preventDefault(); // Stop page from reloading

    // 1. Get User Input
    const start = document.getElementById('startRoom').value.trim();
    const end = document.getElementById('endRoom').value.trim();

    // 2. Clear previous states
    errorMsg.classList.add('hidden');
    resultContainer.style.display = 'none';
    resultContainer.innerHTML = 'Loading route...';
    resultContainer.style.display = 'block';

    try {
        // 3. Call the Python Backend
        // URL: /saveetha-path?start_room=...&end_room=...
        const response = await fetch(`/saveetha-path?start_room=${encodeURIComponent(start)}&end_room=${encodeURIComponent(end)}`);
        
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not find path.");
        }

        // 4. Success! Render the Path
        renderPath(data.distance, data.path);

    } catch (err) {
        // 5. Error Handling
        resultContainer.style.display = 'none';
        errorMsg.textContent = "Error: " + err.message;
        errorMsg.classList.remove('hidden');
    }
});

function renderPath(dist, pathArray) {
    // Basic styling for the result box
    resultContainer.style.display = 'block';
    resultContainer.style.backgroundColor = '#e6fffa'; // Light green bg
    
    // Format the path arrows
    const pathString = pathArray.map(node => `<span>${node}</span>`).join(' <span style="color:#aaa">→</span> ');

    resultContainer.innerHTML = `
        <h3 style="margin-top:0;">Route Found!</h3>
        <p><strong>Total Distance:</strong> ${dist} meters (approx)</p>
        <hr style="border: 1px dashed black; margin: 10px 0;">
        <div style="font-family: monospace; font-size: 1.1em; line-height: 1.6;">
            ${pathString}
        </div>
    `;
    
    // Check dark mode for the result container
    if (document.body.classList.contains('dark-theme')) {
        resultContainer.style.backgroundColor = '#111';
        resultContainer.style.border = '3px solid white';
    }
}