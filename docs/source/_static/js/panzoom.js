function isTouchDevice() {
    return (('ontouchstart' in window) ||
        (navigator.maxTouchPoints > 0) ||
        (navigator.msMaxTouchPoints > 0));
}

window.onload = function () {
    // only add pan and zoom to non-touchable interfaces since they
    // usually implement plan and zoom much better
    if (!isTouchDevice()) {
        var elements = document.querySelectorAll('p.plantuml img');
        elements.forEach(element => {
            const panzoom = Panzoom(element, {
                maxScale: 10,
                duration: 50
            });
            // Panning and zooming using the mouse wheel
            element.parentElement.addEventListener('wheel', panzoom.zoomWithWheel);
            // Code to enable double-click zoom
            element.parentElement.addEventListener('dblclick', function (event) {
                event.preventDefault();
                if (event.shiftKey) {
                    panzoom.zoomOut();
                } else {
                    panzoom.zoomIn();
                }
            });
        });
    }
};
