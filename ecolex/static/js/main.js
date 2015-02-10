var _form_data = null;

$(document).ready(function () {
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

    // initial form value
    var _initial_form_data = $('.search-form').serialize();

    function submit() {
        var data = $('.search-form').serialize();
        if (data != _initial_form_data) {
            /*$.ajax({
                url: '/result/ajax?' + data,
                format: 'JSON',
                success: function (data) {
                    $('#layout-main').html(data.main);
                    $('#filters').html(data.sidebar);
                    _initial_form_data = data;
                    init_all();
                }
            });*/
            $('.search-form').submit();
        } else {
            console.log('No new data');
        }
    }

    function init_all() {
        // initialize tooltips
        // bootstrap tooltips are opt-in
        $('[data-toggle="tooltip"]').tooltip();

        // prevent disabled pagination anchor to trigger page reload
        $('.pagination').on('click', '.disabled', function (e) {
            e.preventDefault();
        });

        // Slider
        $("#slider-years")
          .slider()
          .on('slide', function(event) {
              var min = $('#year-min'),
                  max = $('#year-max');

              min.val(event.value[0]);
              max.val(event.value[1]);
          })
          .on('slideStop', function(event) {
            var min = $('#year-min'),
                max = $('#year-max');

            min.val(event.value[0]);
            max.val(event.value[1]);

            var form_id = $(min).data('formid');
            $(form_id).val($(min).val());

            var form_id = $(max).data('formid');
            $(form_id).val($(max).val());

            submit();
          });

        // Year inputs
        updateYear = function(e) {
          minEl = $('#year-min');
          maxEl = $('#year-max');

          min = $(minEl).val();
          max = $(maxEl).val();

          if (min == '' || typeof min == 'undefined')
            min = $(minEl).attr('min');
          if (max == '' || typeof max == 'undefined')
            max = $(maxEl).attr('max');

          console.log([min, max]);

          $("#slider-years").slider('setValue', [min, max]);
        }

        $('#year-min, #year-max').on('change', updateYear);

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
            onDropdownHidden: function (e) {
                var select = $(this.$select);
                var formid = select.data('formid');

                $(formid).val(select.val());
                // submit now for now
                submit();
            }
        });

        // Type filter - ugly
        $('.filter-type button').click(function (e) {
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
            submit();
        });

        // Treaty -> Type of Document/Field of application filter
        // COP Decision -> Decision Type, Decision Status /Decision Treaty
        $('input[type=checkbox]',
            $('.filter-decision, .filter-treaty')).change(function (e) {
                var current = [];
                var ul = $(this).parents('ul');
                var form_id = ul.data('formid');

                ul.find('input:checked').each(function () {
                    current.push($(this).val());
                });
                $(form_id).val(current);
                // submit now for now
                submit();
            });

        // Year controls
        $('.global-filter input[type=number]').change(function (e) {
            var form_id = $(this).data('formid');
            $(form_id).val($(this).val());
            // submit le form
            submit();
        });
    }

    init_all();
});
