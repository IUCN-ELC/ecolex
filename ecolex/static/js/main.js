// var filters = {

// 	getToggleButtons: function(selector) {
// 		toggleButtons = [];
// 		$(selector).each(function() {
// 			toggleButtons.push(this);
// 		});
// 		return toggleButtons;
// 	},

// 	getFieldsets: function(selector) {
// 		fieldsets = [];
// 		$(selector).each(function() {
// 			fieldsets.push(this);
// 		});
// 		return fieldsets;
// 	},

// 	toggleFieldset: function(button) {

// 	},

// 	init: function( settings ) {
// 		fieldsets = filters.getFieldsets(settings.fieldsetSelector);
// 		toggleButtons = filters.getToggleButtons(settings.toggleButtonsSelector);

// 		filter.pairs = [];

// 		for(i = 0; i < fieldsets.length; i ++) {
// 			fieldset = fieldsets[i];

// 			button = null;

// 			for (j = 0; j < toggleButtons.length; j ++) {
// 				if ('#' + fieldset.id == $(toggleButtons[j]).data('filter')) {
// 					button = toggleButtons[j];
// 					toggleButtons.splice(j, 1);
// 					j = toggleButtons.length;
// 				}
// 			}

// 			if ($(fieldset).attr('disabled')) {
// 				disabled = true;
// 				$(button).removeClass('active');
// 			} else {
// 				disabled = false;
// 				$(button).addClass('active');
// 			}

// 			console.log(button);

// 			data = {
// 				'fieldset': fieldset,
// 				'button': button,
// 				'disabled': disabled
// 			};

// 			pairs.push(data);

// 			$(button).on('click', filter.pairs[filter.pairs.length], function(e) {
// 				disabled = e.data.disabled;
// 				fieldset = e.data.fieldset;
// 				if (disabled) {
// 					console.log('disabling')
// 					$(fieldset).removeAttr('disabled');
// 					$(this).addClass('active');
// 					filter.pairs.disabled
// 				} else {
// 					console.log('enabling')
// 					$(fieldset).attr('disabled', true);
// 					$(this).addClass('active');
// 				}
// 			})


// 			// $(button).on('click', filters.toggleFieldset(this));
// 		}
// 	}

// };

// $(document).ready( filters.init({
// 	toggleButtonsSelector: '[data-filter]',
// 	fieldsetSelector: 'fieldset[id]'
// }));





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

	// With JQuery
	$('#ex1').slider({
		formatter: function(value) {
			return 'Current value: ' + value;
		}
	});
});
