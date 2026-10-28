const behaviorState = {

    keyPressTimes: [],

    clickTimes: [],

    mouseDistance: 0,

    windowStart: performance.now(),

    lastMouseX: null,

    lastMouseY: null,

    lastMouseTime: null
};


// --------------------------------------------------
// Keyboard observation
// --------------------------------------------------

document.addEventListener("keydown", function () {

    const now = performance.now();

    behaviorState.keyPressTimes.push(now);

});


// --------------------------------------------------
// Mouse observation
// --------------------------------------------------

document.addEventListener("mousemove", function (event) {

    const now = performance.now();

    if (
        behaviorState.lastMouseX !== null &&
        behaviorState.lastMouseY !== null &&
        behaviorState.lastMouseTime !== null
    ) {

        const dx =
            event.clientX -
            behaviorState.lastMouseX;

        const dy =
            event.clientY -
            behaviorState.lastMouseY;

        const distance =
            Math.sqrt(
                (dx * dx) +
                (dy * dy)
            );

        behaviorState.mouseDistance += distance;
    }

    behaviorState.lastMouseX =
        event.clientX;

    behaviorState.lastMouseY =
        event.clientY;

    behaviorState.lastMouseTime =
        now;

});


// --------------------------------------------------
// Click observation
// --------------------------------------------------

document.addEventListener("click", function () {

    const now = performance.now();

    behaviorState.clickTimes.push(now);

});


// --------------------------------------------------
// Calculate average
// --------------------------------------------------

function average(values) {

    if (values.length === 0) {
        return 0;
    }

    return values.reduce(
        (sum, value) => sum + value,
        0
    ) / values.length;
}


// --------------------------------------------------
// Calculate variance
// --------------------------------------------------

function variance(values) {

    if (values.length < 2) {
        return 0;
    }

    const mean = average(values);

    return average(
        values.map(
            value =>
                Math.pow(
                    value - mean,
                    2
                )
        )
    );
}


// --------------------------------------------------
// Create observation
// --------------------------------------------------

function calculateBehaviorFeatures() {

    const now = performance.now();

    const elapsedSeconds =
        (
            now -
            behaviorState.windowStart
        ) / 1000;


    // ----------------------------------------------
    // Typing intervals
    // ----------------------------------------------

    const typingIntervals = [];

    for (
        let i = 1;
        i < behaviorState.keyPressTimes.length;
        i++
    ) {

        typingIntervals.push(
            behaviorState.keyPressTimes[i] -
            behaviorState.keyPressTimes[i - 1]
        );

    }


    let typingSpeed = 0;

    if (typingIntervals.length > 0) {

        const averageInterval =
            average(
                typingIntervals
            );

        if (averageInterval > 0) {

            typingSpeed =
                1000 /
                averageInterval;

        }

    }


    const typingIntervalVariance =
        variance(
            typingIntervals
        );


    // ----------------------------------------------
    // Click intervals
    // ----------------------------------------------

    const clickIntervals = [];

    for (
        let i = 1;
        i < behaviorState.clickTimes.length;
        i++
    ) {

        clickIntervals.push(
            behaviorState.clickTimes[i] -
            behaviorState.clickTimes[i - 1]
        );

    }


    let clickInterval = 0;

    if (clickIntervals.length > 0) {

        clickInterval =
            average(
                clickIntervals
            ) / 1000;

    }


    // ----------------------------------------------
    // Mouse speed
    // ----------------------------------------------

    let mouseSpeed = 0;

    if (elapsedSeconds > 0) {

        mouseSpeed =
            behaviorState.mouseDistance /
            elapsedSeconds;

    }


    return {

        typing_speed: typingSpeed,

        typing_interval_variance:
            typingIntervalVariance,

        mouse_speed: mouseSpeed,

        click_interval: clickInterval,

        navigation_interval:
            elapsedSeconds

    };

}


// --------------------------------------------------
// Reset observation window
// --------------------------------------------------

function resetObservationWindow() {

    behaviorState.keyPressTimes = [];

    behaviorState.clickTimes = [];

    behaviorState.mouseDistance = 0;

    behaviorState.windowStart =
        performance.now();

    behaviorState.lastMouseX = null;

    behaviorState.lastMouseY = null;

    behaviorState.lastMouseTime = null;

}


// --------------------------------------------------
// Send observation
// --------------------------------------------------

async function sendObservation() {

    const features =
        calculateBehaviorFeatures();


    console.log(
        "Observation:",
        features
    );


    try {

        const response =
            await fetch(
                "/api/behavior/observation",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            features
                        )
                }
            );


        const data =
            await response.json();


        console.log(
            "Server response:",
            data
        );


        document.getElementById(
            "observationStatus"
        ).textContent =
            "Behavior observation submitted.";


    } catch (error) {

        console.error(
            "Observation error:",
            error
        );

    }


    // Start a fresh observation window.

    resetObservationWindow();

}


// --------------------------------------------------
// Collect every 10 seconds
// --------------------------------------------------

setInterval(
    sendObservation,
    10000
);