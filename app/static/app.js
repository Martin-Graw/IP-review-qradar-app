// This function runs when the HTML page is fully loaded
document.addEventListener('DOMContentLoaded', () => {

    // --- Get references to all our HTML elements ---
    const inputSection = document.getElementById('input_section');
    const reviewSection = document.getElementById('review_section');
    const ipListInput = document.getElementById('ip_list_input');
    const startReviewButton = document.getElementById('start_review_button');
    const ipSpan = document.getElementById('current_ip');
    const whoisDataPre = document.getElementById('whois_data');
    const yesButton = document.getElementById('yes_button');
    const noButton = document.getElementById('no_button');

    // --- State variables to manage the review process ---
    let ipList = [];
    let currentIndex = 0;
    let currentSubnet = null;

    // --- Event Listener for the "Start Review" button ---
    startReviewButton.addEventListener('click', () => {
        // Read the IPs from the textarea, split them by line, and remove any empty lines
        const ips = ipListInput.value.trim().split('\n').filter(ip => ip);
        
        if (ips.length > 0) {
            ipList = ips;
            currentIndex = 0;
            inputSection.style.display = 'none';   // Hide the input section
            reviewSection.style.display = 'block'; // Show the review section
            processNextIp();                       // Start processing the first IP
        } else {
            alert('Please paste a list of IP addresses.');
        }
    });

    // --- Core Functions ---

    // This function advances the review to the next IP in the list
    function moveToNextIp() {
        currentIndex++;
        if (currentIndex < ipList.length) {
            processNextIp();
        } else {
            // We've reached the end of the list
            alert('Review complete! All IPs have been processed.');
            reviewSection.style.display = 'none';  // Hide the review section
            inputSection.style.display = 'block';  // Show the input section again
            ipListInput.value = '';                // Clear the input box
        }
    }

    // This function displays the current IP and fetches its WHOIS data
    function processNextIp() {
        const currentIp = ipList[currentIndex];
        ipSpan.textContent = currentIp;
        whoisDataPre.textContent = 'Loading WHOIS data...';
        currentSubnet = null; // Reset the subnet for the new IP
        fetchWhoisData(currentIp);
    }

    // This is the same function as before to call our backend
    async function fetchWhoisData(ip) {
        try {
            const response = await fetch(`/whois/${ip}`);
            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
            const data = await response.json();

            currentSubnet = data.cidr; // Save the subnet for the "block" button
            const formattedData = `Description: ${data.description}\n` +
                                `CIDR Subnet: ${data.cidr}`;
            whoisDataPre.textContent = formattedData;

        } catch (error) {
            whoisDataPre.textContent = `Error fetching WHOIS data for ${ip}: ${error}`;
        }
    }

    // --- Decision Button Event Listeners ---

    yesButton.addEventListener('click', () => {
        console.log(`Allowed IP: ${ipList[currentIndex]}`);
        moveToNextIp(); // Move to the next IP
    });

noButton.addEventListener('click', async () => {
        if (!currentSubnet) {
            alert('No subnet data available to block.');
            return;
        }

        try {
            // Send the subnet to the /block endpoint using a POST request
            const response = await fetch('/block', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ subnet: currentSubnet }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const resultText = await response.text();
            alert(resultText); // Show the success message from the server
            
            // Now that the block was successful, move to the next IP in the list
            moveToNextIp();

        } catch (error) {
            alert(`Error blocking subnet: ${error}`);
            // We don't move to the next IP if there was an error, so the user can retry.
        }
    });
});
