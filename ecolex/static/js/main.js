var _form_data = null;

$(document).ready(function () {
    $('[data-filter]').on('click', function() {
      target = $(this).data('filter')
      target = $(target);
      $(this).toggleClass('active');

      if (target.attr('disabled')) {
        target.removeAttr('disabled');
      } else {
        target.attr('disabled', true);
      }
    });

   // reload results when the back button was pressed
   $(window).on("popstate", function(e) {
      // history states are tagged in order to ignore popstate events
      // triggered on page load.
      if (history.state.tag !== "ecolex") {
        return;
      }
      // $(".search-form").deserialize(location.search.substring(1));
      $(".search-form").deserialize(history.state.data);
      submit(history.state.data);
   });


    // initial form value
    var _initial_form_data = $('.search-form').serialize();

    init = 0;
    function push_and_submit() {
        var data = $('.search-form').serialize();
        history.pushState({data : data, tag: 'ecolex'} , '', '?' + data);
        submit(data);
    }

    function submit(data) {
        if (data != _initial_form_data) {
            $('main').block({ message: null });
            $.ajax({
                url: '/result/ajax?' + data,
                format: 'JSON',
                success: function (data) {
                    $('#layout-main').html(data.main);
                    $('#filters').html(data.sidebar);
                    _initial_form_data = data;
                    $(".search-form").deserialize(data);
                    init_all();
                    $('main').unblock();
                },
                error: function (e) {
                    $('main').unblock();
                }
            });
            //$('.search-form').submit();
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

            push_and_submit();
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
            // filterBehavior: 'value',
            numberDisplayed: 1,
            nonSelectedText: 'Nothing selected',
            enableCaseInsensitiveFiltering: true,
            maxHeight: 240,
            onDropdownHidden: function (e) {
                var select = $(this.$select);
                var formid = select.data('formid');

                $(formid).val(select.val());
                // submit now for now
                push_and_submit();
            },
            onDropdownShown: function(e) {
                search = $(e.target).find('.multiselect-search').focus();
            }
        });

        var type_filter_handler_base = function (e) {
            // Type filter - ugly
            $('.filter-type button').click(function (e) {
                var current = $('#id_type').val() || [];
                var toggle_value = $(this).data('value');
                if (current.indexOf(toggle_value) == -1) {
                    current.push(toggle_value);
                } else {
                    current.splice(current.indexOf(toggle_value), 1);
                }
                $('#id_type').val(current);
            });
        };

       // FIXME(catalinb): duplicate code. Ship it!
       $('.filter-type.homepage button').click(function (e) {
            var current = $('#id_type').val() || [];
            var toggle_value = $(this).data('value');
            if (current.indexOf(toggle_value) == -1) {
                current.push(toggle_value);
            } else {
                current.splice(current.indexOf(toggle_value), 1);
            }
            $('#id_type').val(current);
            // submit now for now
            $(".search-form").submit();
        });

        $('.filter-type.results-page button').click(function (e) {
            var current = $('#id_type').val() || [];
            var toggle_value = $(this).data('value');
            if (current.indexOf(toggle_value) == -1) {
                current.push(toggle_value);
            } else {
                current.splice(current.indexOf(toggle_value), 1);
            }
            $('#id_type').val(current);
            // submit now for now
            push_and_submit();
        });

        console.log("set");

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
                push_and_submit();
            });

        // Year controls
        $('.global-filter input[type=number]').change(function (e) {
            var form_id = $(this).data('formid');
            $(form_id).val($(this).val());
            // submit le form
            push_and_submit();
        });

        // Sortby controls
        $('.sortby').click(function (e) {
            e.preventDefault();
            var value = $(this).data('sortby');
            $('#id_sortby').val(value);
            push_and_submit();
        });

        // Reset button
        $('input[type=reset]').click(function (e) {
            e.preventDefault();
            var data = {
                'q': $('#id_q').val(),
                'type': $('#id_type').val()
            };
            $('.search-form select, .search-form input').each(function() {
                $(this).val('')
            });
            $('#id_q').val(data.q);
            $('#id_type').val(data.type);

            push_and_submit();
        });

        // Tag manager

        var states = new Bloodhound({
          name: 'animals',
          local: [{ val: 'dog' }, { val: 'pig' }, { val: 'moose' }],
          // remote: 'http://example.com/animals?q=%QUERY',
          datumTokenizer: function(d) {
            return Bloodhound.tokenizers.whitespace(d.val);
          },
          queryTokenizer: Bloodhound.tokenizers.whitespace
        });

        states.initialize();

        var substringMatcher = function(strs) {
          return function findMatches(q, cb) {
            var matches, substrRegex;
        
            // an array that will be populated with substring matches
            matches = [];
        
            // regex used to determine if a string contains the substring `q`
            substrRegex = new RegExp(q, 'i');
        
            // iterate through the pool of strings and for any string that
            // contains the substring `q`, add it to the `matches` array
            $.each(strs, function(i, str) {
              if (substrRegex.test(str)) {
                // the typeahead jQuery plugin expects suggestions to a
                // JavaScript object, refer to typeahead docs for more info
                matches.push({ value: str });
              }
            });
        
            cb(matches);
          };
        };
         
        var states = ['Access right', 'Alien species', 'Animal health', 'Animal production', 'Biology',
           'Birds', 'Climate change', 'Environment', 'Farming', 'Health', 'Insects', 'Marine area',
           'Navigation', 'Public forrest', 'Reptiles', 'Turism', 'Wild fauna'
        ]; 

        $('.tm-input').each(function() {
            var self = this;
            $(this).tagsManager({
                tagsContainer: $('<ul/>', { class: 'tm-taglist' }),
                tagCloseIcon: '',
            })

            $(this).wrap( $('<div/>', { class: 'tm-wrapper' }) );
            var label = $('<label/>', {
                'class': 'tm-label',
                'for': $(this).attr('id'),
                // 'text': $(this).attr('placeholder')
            });
            $(this).before(label);

            $(this).typeahead({
              hint: false,
              highlight: true,
              minLength: 1,
            },
            {
              name: 'states',
              displayKey: 'value',
              source: substringMatcher(states)
            });

            $(this).on('blur', function() {
                $(this).val('');
            });
        });

    }

    init_all();
});
    
