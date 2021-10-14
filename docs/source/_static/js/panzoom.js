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
            element.addEventListener('click', function (event) {
                event.preventDefault();
                var panel = jsPanel.modal.create({
                    contentAjax: {url: element.src},
                    contentSize: 'auto auto',
                    panelSize: '90%',
                    theme: 'none',
                    boxShadow: 0,
                    dragit: false,
                    resizeit: false,
                    addCloseControl: 1,
                    header: false,
                    footerToolbar: '<span style="vertical-align:center">Mouse wheel or double-click/shift+double-click for zoom. Esc to exit.</span>'
                });
                var panzoom = Panzoom(panel.content, {
                    maxScale: 10,
                    duration: 50,
                });
                // zoom a bit out to show the whole diagram
                panzoom.zoom(0.8);
                // Panning and zooming using the mouse wheel
                panel.content.parentElement.addEventListener('wheel', panzoom.zoomWithWheel);
                // Code to enable double-click zoom
                panel.content.parentElement.addEventListener('dblclick', function (event) {
                    event.preventDefault();
                    if (event.shiftKey) {
                        panzoom.zoomOut();
                    } else {
                        panzoom.zoomIn();
                    }
                });
            });
        });
    }
};
