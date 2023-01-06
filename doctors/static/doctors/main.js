// helper functions to show and hide elements
function showElement(elt_id) {
    document.querySelector(`#${elt_id}`).classList.remove('hidden');
}
function hideElement(elt_id) {
    document.querySelector(`#${elt_id}`).classList.add('hidden');
}


//
// functions used in the pages to register, to view and update user details
//

// allow doctors to choose a specialty and provide a description
// used on the registration page (user_form.html)
function showDoctorFields() {
    if (document.querySelector('#id_is_doctor').checked) {
        showElement('specialty-field');
        showElement('description-field');
    } else {
        hideElement('specialty-field');
        hideElement('description-field');
    }
}

// helper function to upload a picture asynchronously
// used on the user detail page
function submitPicture() {
    const ENDPOINT = "/users/upload";
    function show_error(error_text) {
        errorElt = document.querySelector("#error-message");
        errorElt.textContent = error_text;
        errorElt.style.display = 'block';
    }
    if (document.querySelector("#id_picture").value === "") {
        show_error("You did not choose a file.");
        return;
    }
    const form = document.querySelector('#picture-form')
    let done = false;
    fetch(ENDPOINT, {
        method: "POST",
        body: new FormData(form),
    })
    .then(response => {
        if (response.status === 204) { // no content status code
            done = true;
            window.location.reload();
        } else if (response.status === 422) {  // unprocessable entity status code
            return response.json()
        } else {
            throw new Error(`Got response status code ${response.status}`);
        }
    })
    .then(data => {
        if (!done && data) {
            show_error(data.errors.picture[0])
        }
    })
    .catch((error) => {
        console.log(`POST request to ${ENDPOINT} error:\n${error}`);
    });
}


//
// functions used in the index page to search for doctors
//

// Cache used by the function searchDoctors. It caches search results to improve 
// performance, for example when user hits backspace in the search box
const doctors_cache = new Map();
function searchDoctors(event) {
    function showResults(results) {
        results_container.innerHTML = "";
        results.forEach(doctor => {
            results_container.append(buildDoctorCard(doctor));
        });
    }
    const results_container = document.querySelector('#results_container');
    search_term = event.target.value.trim();
    if (search_term === '') {
        // clear any previous results
        results_container.innerHTML = "";
        return;
    }
    // check whether the search_term is in the cache
    const results = doctors_cache.get(search_term);
    if (results) {
        showResults(results);
        // we are done!
        return;
    }

    // no cached results, so we need to fetch
    const ENDPOINT = "/search/";
    const api_path = `${ENDPOINT}?search_term=${encodeURIComponent(search_term)}`;
    fetch(api_path)
        .then(response => {
            if (response.status !== 200) {
                throw new Error(`Got response status code ${response.status}`);
            } else {
                return response.json();
            }
        })
        .then(({results}) => {
            // mark the text that matched the searh terms
            results.forEach(doctor => {
                doctor.doctor_name = markMatches(doctor.doctor_name, search_term)
                doctor.doctor_specialty = markMatches(doctor.doctor_specialty, search_term)
            });
            // cache the results
            doctors_cache.set(search_term, results);
            showResults(results);
        })
        .catch((error) => {
            console.log(`GET request to ${ENDPOINT} error:\n${error}`);
        });
}

// used to display each of the search results
function buildDoctorCard({doctor_id, doctor_name, doctor_specialty, doctor_img}) {
    const doctor_card = document.createElement('div');
    doctor_card.className = "card card-doctor-results mb-3";
    doctor_card.innerHTML = `<div class="row g-0" onclick="location.href='/book/${doctor_id}';">
        <div class="col-sm-3">
            <img src="/images/${doctor_img}" class="img-fluid rounded-start">
        </div>
        <div class="col-sm-9">
            <div class="card-body">
                <h6 class="card-title">Doctor ${doctor_name}</h6>
                <p class="card-text">${doctor_specialty}</p>
            </div>
        </div>
    </div>`;
    return doctor_card;
}

// Mark the substrings that matched the search term
function markMatches(text, search_term) {
    return text.replace(new RegExp(`(${search_term})`,"gi"), (matched_text) => {
        return `<span class="matched">${matched_text}</span>`;
    });

}


//
// functions used in the booking page
// 
function getAvailabilities(event, doctor_id, date) {
    card = event.currentTarget.parentNode;
    if (card.classList.contains('closed')) {
        // open the card
        card.classList.remove('closed')
        // show the symbow with arrow up
        card.querySelector(".bi-chevron-down").classList.add('hidden');
        card.querySelector(".bi-chevron-up").classList.remove('hidden');
        // populate the modal form with the date in case the user 
        // confirms the appointment
        const dateString = card.querySelector('.dateLongFormat').textContent;
        document.querySelector('#dateLongFormat').textContent = dateString;
        document.querySelector('#dateId').value = date;
    } else {
        // close the card
        card.classList.add('closed')
        // show the symbow with arrow down
        card.querySelector(".bi-chevron-up").classList.add('hidden');
        card.querySelector(".bi-chevron-down").classList.remove('hidden');
        card.querySelector('.time-slots').innerHTML = '';
    }
    // fetch time slots for the given date
    const ENDPOINT = "/book/slots";
    const api_path = `${ENDPOINT}?doctor_id=${encodeURIComponent(doctor_id)}&date=${encodeURIComponent(date)}`;
    fetch(api_path)
        .then(response => {
            if (response.status !== 200) {
                throw new Error(`Got response status code ${response.status}`);
            } else {
                return response.json();
            }
        })
        .then(({time_slots}) => {
            // mark the text that matched the searh terms
            const container = card.querySelector('.time-slots');
            container.innerHTML = '';
            time_slots.forEach(time_slot => {
                const time_box = document.createElement('div');
                time_box.setAttribute("data-bs-toggle", "modal");
                time_box.setAttribute("data-bs-target", "#ConfirmBookingModal");
                time_box.className = 'time-box';
                time_box.textContent = time_slot;
                time_box.onclick = initializeConfirmBookingModal;
                container.append(time_box);
            });
        })
        .catch((error) => {
            console.log(`GET request to ${ENDPOINT} error:\n${error}`);
        });
}

function initializeConfirmBookingModal(event) {
    const chosenTime = event.target.textContent;
    document.querySelector('#time').textContent = chosenTime;
    document.querySelector('#timeId').value = chosenTime;
}

function confirmBooking(event) {
    const form = document.querySelector('#appointment-book-form');
    ENDPOINT = "/book/confirm"; 
    fetch(ENDPOINT, {
        method: "POST",
        body: new FormData(form),
    })
    .then(response => {
        if (response.status === 204) { // no content status code
            window.location.href = `/appointments`;
        } else {
            throw new Error(`Got response status code ${response.status}`);
        }
    })
    .catch((error) => {
        console.log(`POST request to ${ENDPOINT} error:\n${error}`);
        window.location.reload();
    });
}


//
// functions used in the appointments page
//
function initializeConfirmCancellationModal(event) {
    document.querySelector('#date').textContent = event.target.dataset.date;
    document.querySelector('#time').textContent = event.target.dataset.time;
    document.querySelector('#person').textContent = event.target.dataset.person;
    document.querySelector('#appointmentId').value = event.target.dataset.appointmentId;
}

function confirmCancellation() {
    const form = document.querySelector('#appointment-cancel-form');
    ENDPOINT = "/appointments/cancel"; 
    fetch(ENDPOINT, {
        method: "POST",
        body: new FormData(form),
    })
    .then(response => {
        if (response.status === 204) { // no content status code
            window.location.reload();
        } else {
            throw new Error(`Got response status code ${response.status}`);
        }
    })
    .catch((error) => {
        console.log(`POST request to ${ENDPOINT} error:\n${error}`);
        window.location.reload();
    });
}