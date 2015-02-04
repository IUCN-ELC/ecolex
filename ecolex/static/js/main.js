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
});
