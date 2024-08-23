(function($) {
    $.fn.initSlider = function() {
        this.each(function() {
            var $range_container = $(this);
            var $slider = $range_container.find('#slider-range');
            var $minLabel = $range_container.find('#min');
            var $maxLabel = $range_container.find('#max');

            var min = parseFloat($range_container.data('min'));
            var max = parseFloat($range_container.data('max'));
            var valuesArray = $range_container.data('values');
            if (!Array.isArray(valuesArray) || valuesArray.length !== 2) {
                console.error('Invalid data-values attribute:', valuesArray);
                valuesArray = [min, max]; // Fallback values
            }
            var step = parseFloat($range_container.data('step'));

            $slider.slider({
                range: true,
                min: min,
                max: max,
                values: valuesArray,
                step: step,
                slide: function(event, ui) {
                    $minLabel.html($slider.slider('values', 0)).position({
                        my: 'center bottom',
                        at: 'center top',
                        of: $slider.find('.ui-slider-handle').eq(0),
                        offset: "0, 10"
                    });

                    $maxLabel.html($slider.slider('values', 1)).position({
                        my: 'center bottom',
                        at: 'center top',
                        of: $slider.find('.ui-slider-handle').eq(1),
                        offset: "0, 10"
                    });
                },
                change: function(event, ui) {
                    onSliderChanged();
                }
            });

            $minLabel.html($slider.slider('values', 0)).position({
                my: 'center bottom',
                at: 'center top',
                of: $slider.find('.ui-slider-handle').eq(0),
                offset: "0, 10"
            });

            $maxLabel.html($slider.slider('values', 1)).position({
                my: 'center bottom',
                at: 'center top',
                of: $slider.find('.ui-slider-handle').eq(1),
                offset: "0, 10"
            });

            
        });

        return this;
    };

    $.fn.refreshSlider = function() {
        this.each(function() {
            var $range_container = $(this);
            var $slider = $range_container.find('#slider-range');
            var $minLabel = $range_container.find('#min');
            var $maxLabel = $range_container.find('#max');

            $minLabel.html($slider.slider('values', 0)).position({
                my: 'center bottom',
                at: 'center top',
                of: $slider.find('.ui-slider-handle').eq(0),
                offset: "0, 10"
            });

            $maxLabel.html($slider.slider('values', 1)).position({
                my: 'center bottom',
                at: 'center top',
                of: $slider.find('.ui-slider-handle').eq(1),
                offset: "0, 10"
            });
            
        });

        return this;
    };

    // workaround -  convert touch to mouse events
    jQuery(document).on('touchstart', '#slider-range .ui-slider-handle', function (e) {
        let t = e.touches[0] || e;
        jQuery(this).addClass('ui-state-hover').addClass('ui-state-active').addClass('ui-state-focus')
        var newEvent = new MouseEvent('mousedown', {
          screenX: t.screenX, screenY: t.screenY,
          clientX: t.clientX, clientY: t.clientY,
          relatedTarget: t.target,
        })
        Object.defineProperty(newEvent, 'target', {value: t.target, enumerable: true});
        Object.defineProperty(newEvent, 'currentTarget', {value: t.target, enumerable: true});
        jQuery(this).parent().slider("instance")._mouseDown(newEvent)
    });
    jQuery(document).on('touchend', '#slider-range .ui-slider-handle', function (e) {
        let t = e.touches[0] || e;
        jQuery(this).removeClass('ui-state-hover').removeClass('ui-state-active').removeClass('ui-state-focus')
        var newEvent = new MouseEvent('mouseup', {
          screenX: t.screenX, screenY: t.screenY,
          clientX: t.clientX, clientY: t.clientY,
          relatedTarget: t.target,
        })
        Object.defineProperty(newEvent, 'target', {value: t.target, enumerable: true});
        Object.defineProperty(newEvent, 'currentTarget', {value: t.target, enumerable: true});
        jQuery(this).parent().slider("instance")._mouseUp(newEvent)
    });
    jQuery(document).on('touchmove', '#slider-range .ui-slider-handle', function (e) {
        let t = e.touches[0] || e;
        var newEvent = new MouseEvent('mousemove', {
          screenX: t.screenX, screenY: t.screenY,
          clientX: t.clientX, clientY: t.clientY,
          relatedTarget: t.target,
          'bubbles': true,
          'cancelable': true,
        });
        Object.defineProperty(newEvent, 'target', {value: t.target, enumerable: true});
        Object.defineProperty(newEvent, 'currentTarget', {value: t.target, enumerable: true});
        jQuery(this).parent().slider("instance")._mouseMove(newEvent);
    });
})(jQuery);
