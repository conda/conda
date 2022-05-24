function isTouchDevice() {
    return (('ontouchstart' in window) ||
        (navigator.maxTouchPoints > 0) ||
        (navigator.msMaxTouchPoints > 0));
}

function initSVG(xhr, panel) {
    // store SVG response in content
    panel.content.innerHTML = xhr.responseText;
    var svg = $(panel.content).find("svg").eq(0);

    // patch content to center svg
    $(panel.content).css("display", "grid");
    svg.css("margin", "auto");

    // resize/reposition modal
    panel.resize({
        width: () => {
            return Math.min(svg.width(), $(window).width() * 0.9);
        },
        height: () => {
            return Math.min(
                svg.height() +
                $(panel).find(".jsPanel-hdr").eq(0).height() +
                $(panel).find(".jsPanel-ftr").eq(0).height(),
                $(window).height() * 0.9
            );
        }
    });
    panel.reposition();

    // scale svg to fit
    var xscale = $(panel.content).width() / svg.width();
    var yscale = $(panel.content).height() / svg.height();
    var scale = (xscale < yscale) ? xscale : yscale;
    svg.width(svg.width() * scale);
    svg.height(svg.height() * scale);

    // initializing panzoom object
    var panzoom = Panzoom(svg.get(0), {
        duration: 50,
        minScale: 1,
        maxScale: 20,
        step: 0.5,
    });

    // ensure slider uses the same min/max/step as panzoom
    var slider = $("#panzoom-slider")
    slider.attr("min", 1);
    slider.attr("max", 10);
    slider.attr("step", 0.5);
    slider.attr("value", 1);

    // panning and zooming using the mouse wheel
    $(panel.content).on("wheel", function (event) {
        event.preventDefault();
        panzoom.zoomWithWheel(event.originalEvent);
        slider.val(panzoom.getScale());
    });

    // code to enable double-click zoom
    $(panel.content).dblclick(function (event) {
        event.preventDefault();
        if (event.shiftKey) {
            panzoom.zoomOut();
        } else {
            panzoom.zoomIn();
        }
        slider.val(panzoom.getScale());
    });

    // button zoom
    $("#panzoom-out").click(function () {
        panzoom.zoomOut();
        slider.val(panzoom.getScale());
    });
    $("#panzoom-in").click(function () {
        panzoom.zoomIn();
        slider.val(panzoom.getScale());
    });

    // slider zoom
    slider.on("change", function () {
        panzoom.zoom($(this).val());
    });

    // button reset
    $("#panzoom-reset").click(function () {
        panzoom.reset();
        slider.val(panzoom.getScale());
    });
}

function getTitle(element) {
    // step through parents searching for h2/h3
    // once we find a h2 we stop, finding a h3 is optional
    var h2title, h3title, obj = $(element);
    while (!h2title && obj != window.document) {
        var h2 = obj.siblings("h2"), h3 = obj.siblings("h3");
        if (h2.length) { h2title = h2.eq(0).text(); }
        if (h3.length) { h3title = h3.eq(0).text(); }
        obj = obj.parent();
    }
    // combine titles
    var title = h2title;
    if (h3title) {
        title = title + ' ' + h3title
    }
    // remove non-printable chars from title
    title = title.replace(/[^\x20-\x7e]/g, '');

    return title;
}

function getFooter() {
    return `
        <span class="desc">
            <i class="fa fa-search" aria-hidden="true"></i> Mouse wheel or double-click/shift+double-click for zoom.<br />
            <i class="fa fa-arrows" aria-hidden="true"></i> Click and drag to move.<br />
            <i class="fa fa-times" aria-hidden="true"></i> Esc to exit.
        </span>
        <span class="buttons">
            <button id="panzoom-out" type="button" style="margin-right: 5px;">
                <i class="fa fa-search-minus" aria-hidden="true"></i>
            </button>
            <input id="panzoom-slider" type="range" style="margin-right: 5px;" />
            <button id="panzoom-in" type="button" style="margin-right: 5px;">
                <i class="fa fa-search-plus" aria-hidden="true"></i>
            </button>
            <button id="panzoom-reset" type="button">
                <i class="fa fa-refresh" aria-hidden="true"></i> Reset
            </button>
        </span>
    `;
}

window.onload = function () {
    // only add pan and zoom to non-touchable interfaces since they
    // usually implement plan and zoom much better
    if (!isTouchDevice()) {
        var elements = document.querySelectorAll('p.plantuml img');
        elements.forEach(element => {
            element.addEventListener('click', function (event) {
                event.preventDefault();
                jsPanel.modal.create({
                    contentAjax: {
                        url: element.src,
                        done: initSVG,
                    },
                    theme: 'none',
                    boxShadow: 0,
                    dragit: false,
                    resizeit: false,
                    headerTitle: getTitle(element),
                    footerToolbar: getFooter,
                });
            });
        });
    };
};
