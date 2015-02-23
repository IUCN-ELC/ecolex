var _form_data = null;

$(document).ready(function () {
    $('[data-filter]').on('click', function () {
        target = $(this).data('filter')
        target = $(target);
        $(this).toggleClass('active');

        if (target.attr('disabled')) {
            target.removeAttr('disabled');
        } else {
            target.attr('disabled', true);
        }
    });

    // set initial history entry
    if (!history.state) {
        var data = $('.search-form').serialize();
        history.replaceState({data: data, tag: 'ecolex'}, '', '?' + data);
    }

    // reload results when the back button was pressed
    $(window).on("popstate", function (e) {
        // history states are tagged in order to ignore popstate events
        // triggered on page load.
        if (!history.state || history.state.tag !== "ecolex") {
            return;
        }
        // $(".search-form").deserialize(location.search.substring(1));
        $(".search-form").deserialize(history.state.data);
        submit(history.state.data);
    });


    // initial form value
    var _initial_form_data = $('.search-form').serialize();

    function debounce(func, wait, immediate) {
        var timeout;
        return function () {
            var context = this, args = arguments;
            var later = function () {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    function push_and_submit(ajax) {
        return debounce(function () {
            _push_and_submit(ajax);
        }, 500)();
    }

    function _push_and_submit(ajax) {
        if (ajax) {
            var data = $('.search-form').serialize();
            history.pushState({data: data, tag: 'ecolex'}, '', '?' + data);
            submit(data);
        } else {
            $('.search-form').submit();
        }
    }

    function submit(serialized_form_data) {
        if (serialized_form_data != _initial_form_data) {
            $('main').block({
              message: '<img src="/static/img/ajax-spinner.gif" width="48" height="48"><h3 style="color: #666; margin: 0;">Updating results<h3>',
              centerY: false,
              css: {
                padding: '0',
                margin: '0',
                border: '0',
                top: '169px',
                color: "#666",
                backgroundColor: 'transparent',
              },
              overlayCSS: {
                backgroundColor:  '#ccc',
                opacity:          0.9,
              }
            });
            $.ajax({
                url: '/result/ajax?' + serialized_form_data,
                format: 'JSON',
                success: function (data) {
                    $('#layout-main').html(data.main);
                    $('#filters').html(data.sidebar);
                    $("#search-form-inputs").html(data.form_inputs);
                    _initial_form_data = serialized_form_data;
                    $(".search-form").deserialize(serialized_form_data);
                    init_all();
                    $('main').unblock();
                    // for bootstrap tour
                    $("body").trigger('onajax');
                },
                error: function (e) {
                    $('main').unblock();
                }
            });
        } else {
            console.log('No new data, not submitting.');
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
            .on('slide', function (event) {
                var min = $('#year-min'),
                    max = $('#year-max');

                min.val(event.value[0]);
                max.val(event.value[1]);
            })
            .on('slideStop', function (event) {
                var min = $('#year-min'),
                    max = $('#year-max');

                min.val(event.value[0]);
                max.val(event.value[1]);

                var form_id = $(min).data('formid');
                $(form_id).val($(min).val());

                var form_id = $(max).data('formid');
                $(form_id).val($(max).val());

                push_and_submit(true);
            });

        // Year inputs
        updateYear = function (e) {
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
                push_and_submit(true);
            },
            onDropdownShown: function (e) {
                search = $(e.target).find('.multiselect-search').focus();
            }
        });

        $('.filter-type button').click(function (e) {
            var current = $('#id_type').val() || [];
            var toggle_value = $(this).data('value');
            var is_homepage = $(this).parents().hasClass('homepage');
            if (current.indexOf(toggle_value) == -1) {
                current.push(toggle_value);
            } else {
                current.splice(current.indexOf(toggle_value), 1);
            }
            $('#id_type').val(current);
            // submit now for now
            if (is_homepage)
                push_and_submit(false);
            else
                push_and_submit(true);
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
                push_and_submit(true);
            });

        // Year controls
        $('.global-filter input[type=number]').change(function (e) {
            var form_id = $(this).data('formid');
            $(form_id).val($(this).val());
            // submit le form
            push_and_submit(true);
        });

        // Sortby controls
        $('.sortby').click(function (e) {
            e.preventDefault();
            var value = $(this).data('sortby');
            $('#id_sortby').val(value);
            push_and_submit(true);
        });

        $('button[type=submit]').click(function (e) {
            e.preventDefault();
            var is_homepage = $(this).parents().hasClass('homepage');
            if (is_homepage)
                push_and_submit(false);
            else
                push_and_submit(true);
        });

        $('#suggestion-link').click(function (e) {
            e.preventDefault();
            var value = $(this).text();
            $('#search').val(value);
            push_and_submit(true);
        });

        // Reset button
        $('input[type=reset]').click(function (e) {
            e.preventDefault();
            var data = {
                'q': $('#id_q').val(),
                'type': $('#id_type').val()
            };
            $('.search-form select, .search-form input').each(function () {
                $(this).val('')
            });
            $('#id_q').val(data.q);
            $('#id_type').val(data.type);

            push_and_submit(true);
        });

        // Tag manager
        var substringMatcher = function (strs) {
            return function findMatches(q, cb) {
                var matches, substrRegex;

                // an array that will be populated with substring matches
                matches = [];

                // regex used to determine if a string contains the substring `q`
                substrRegex = new RegExp(q, 'i');

                // iterate through the pool of strings and for any string that
                // contains the substring `q`, add it to the `matches` array
                $.each(strs, function (i, str) {
                    if (substrRegex.test(str)) {
                        // the typeahead jQuery plugin expects suggestions to a
                        // JavaScript object, refer to typeahead docs for more info
                        matches.push({'value': str});
                    }
                });

                cb(matches);
            };
        };

        var tagValidator = function (strs) {
            return function (tag) {
                return (strs.indexOf(tag) !== -1);
            }
        };

        $(".tag-select").each(function () {
            var suggestions = [];
            var preselected = [];
            $("#options option", this).each(function (i, opt) {
                var selected = $(opt).attr("selected");
                var entry = opt.innerHTML;
                if (selected)
                    preselected.push(entry);
                suggestions.push(entry);
            });

            function get_values(tags) {
                var result = [];
                for (var j = 0; j < tags.length; j++) {
                    var tag = tags[j];
                    var parts = tag.split(" ");
                    parts.pop();
                    tag = parts.join(" ");
                    result.push(tag);
                }
                return result;
            }

            $('.tm-input', this).each(function () {
                var self = this;
                $(this).tagsManager({
                    tagsContainer: $('<ul/>', { class: 'tm-taglist' }),
                    tagCloseIcon: '',
                    prefilled: preselected,
                    validator: tagValidator(suggestions)
                }).on("tm:spliced",function (e) {
                    var formid = $(this).data('formid');
                    var value = $(this).tagsManager('tags');
                    $(formid).val(get_values(value));
                    push_and_submit(true);
                }).on("tm:pushed", function (e) {
                    var formid = $(this).data('formid');
                    var value = $(this).tagsManager('tags');
                    $(formid).val(get_values(value));
                    push_and_submit(true);
                });

                $(this).wrap($('<div/>', { class: 'tm-wrapper' }));

                labelFor = $(this).attr('data-formid');
                labelFor = labelFor.substr(1, labelFor.length); // remove #
                label = $('<label/>', {
                    'class': 'tm-label',
                    'for': labelFor
                    // 'text': $(this).attr('placeholder')
                });
                $(this).before(label);

                $(this).typeahead({
                        hint: false,
                        highlight: true,
                        minLength: 0
                    },
                    {
                        name: 'states',
                        displayKey: 'value',
                        source: substringMatcher(suggestions)
                    });

                $(this).on('blur', function () {
                    $(this).val('');
                });
            });
        });

    }

    init_all();
});
