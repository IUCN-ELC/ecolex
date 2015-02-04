$(document).ready(function() {
	// $('[data-filter]').on('click', function() {
	// 	target = $(this).data('filter')
	// 	target = $(target);
	// 	$(this).toggleClass('active');

	// 	if (target.attr('disabled')) {
	// 		target.removeAttr('disabled');
	// 	} else {
	// 		target.attr('disabled', true);
	// 	}
	// });

	// initialize tooltips
	// bootstrap tooltips are opt-in
	$('[data-toggle="tooltip"]').tooltip();

	// prevent disabled pagination anchor to trigger page reload
	$('.pagination').on('click', '.disabled', function(e) {
		e.preventDefault();
	});

	// Slider
	$('#filter-years').slider({
		formatter: function(value) {
			return 'Current value: ' + value;
		}
	});

	// Multiselect
	$('select[multiple]').multiselect();

    // Type filter - ugly
    $('.filter-type button').click(function(e) {
        var current = $('#id_type').val() || [];
        var toggle_value = $(this).data('value');
        if (!current) {
            current = [toggle_value];
        } else {
            if (current.indexOf(toggle_value) == -1) {
                current.push(toggle_value);
            } else {
                current.splice(current.indexOf(toggle_value), 1);
            }
        }
        $('#id_type').val(current);
        $(this).toggleClass('btn-default');
        // submit now for now
        $('.search-form').submit();
    });
});
