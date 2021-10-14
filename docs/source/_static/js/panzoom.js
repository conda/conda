window.onload = function () {
    var elements = document.querySelectorAll('p.plantuml img');

    elements.forEach(element => {
        const panzoom = Panzoom(element, {
            maxScale: 10,
            duration: 50
        });
        // Panning and pinch zooming are bound automatically (unless disablePan is true).
        // There are several available methods for zooming
        // that can be bound on button clicks or mousewheel.
        element.parentElement.addEventListener('wheel', panzoom.zoomWithWheel);
        // Code to enable double-click zoom, disabled because it may interact
        // badly on mobile.
        // element.parentElement.addEventListener('dblclick', function (event) {
        //     event.preventDefault();
        //     if (event.shiftKey) {
        //         panzoom.zoomOut();
        //     } else {
        //         panzoom.zoomIn();
        //     }
        // });
    });
};
