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
    $('select[multiple]').multiselect({
        buttonClass: '',
        buttonContainer: '<div class="multiselect-wrapper" />', // '<div class="btn-group multiselect-wrapper" />',
        disableIfEmpty: true,
        enableFiltering: true,
        enableCaseInsensitiveFiltering: true,
        filterBehavior: 'value',
        numberDisplayed: 1,
        nonSelectedText: 'Nothing selected',
        // filterPlaceholder: "porn",
        maxHeight: 240,
        onDropdownHidden: function(e) {
            var select = $(this.$select);
            var formid = select.data('formid');

            $(formid).val(select.val());
            // submit now for now
            $('.search-form').submit();
            // check if actual changes
        }
    });

    // Type filter - ugly
    $('.filter-type button').click(function(e) {
        var current = $('#id_type').val() || [];
        var toggle_value = $(this).data('value');
        if (current.length == 2) {
            current = [toggle_value];
        } else {
            if (current.indexOf(toggle_value) == -1) {
                current.push(toggle_value);
            } else {
                current.splice(current.indexOf(toggle_value), 1);
            }
        }
        $('#id_type').val(current);
        // submit now for now
        $('.search-form').submit();
    });

    // Treaty -> Type of Document/Field of application filter
    // COP Decision -> Decision Type, Decision Status /Decision Treaty
    $('input[type=checkbox]',
      $('.filter-decision, .filter-treaty')).change(function (e) {
        var current = [];
        var ul = $(this).parents('ul');
        var form_id = ul.data('formid');

        ul.find('input:checked').each(function (){
            current.push($(this).val());
        });
        $(form_id).val(current);
        // submit now for now
        $('.search-form').submit();
    })
});
