var _form_data = null;

$(document).ready(function() {

/* our custom select2 adapter */
var CachingAjaxAdapter;
$.fn.select2.amd.require([
    'select2/data/array',
    'select2/data/ajax',
    'select2/utils',
    'select2/results',
    'select2/dropdown/infiniteScroll',
    'select2/diacritics'
], function (ArrayAdapter, AjaxAdapter, Utils, Results, InfiniteScroll,
             DIACRITICS) {
    CachingAjaxAdapter = function ($element, options) {
        var data = options.get('data') || [];
        self._data = data;

        $.extend(options.options, this._getDefaults());
        CachingAjaxAdapter.__super__.constructor.call(this, $element, options);
    };

    Utils.Extend(CachingAjaxAdapter, AjaxAdapter);

    var CustomResults = Utils.Decorate(Results, InfiniteScroll);

    CustomResults.prototype.template = function (result, container) {
        // hack to get the current query term, because select2
        var term;
        if (!result.loading) term = this.$element._term;

        var content = CustomResults.prototype._template(result, term, container);

        if (content == null) {
            container.style.display = 'none';
        } else if (typeof content === 'string') {
            container.innerHTML = content;
        } else {
            $(container).append(content);
        }
    };

    CustomResults.prototype._template = function (result, term) {
        // .loading means this item is the "loading" message
        if (result.loading) return result.text;

        var text = CustomResults.prototype._highlight(result.text, term);

        return '' +
            '<div class="clearfix">' +
            '<div class="pull-left">' + text + '</div>' +
            '<div class="pull-right">' + result.count + '</div>' +
            '</div>';
    };

    var _stripDiacritics = function (text) {
        // courtesy of upstream
        function match(a) {
            return DIACRITICS[a] || a;
        }
        return text.replace(/[^\u0000-\u007E]/g, match);
    };

    CustomResults.prototype._highlight = function (text, term) {
        // this actually does both highlighting and escaping

        if (!term) return text;

        // TODO: regex-escape the term
        // TODO: should match all of the given terms. like the backend.
        // TODO: unify with below
        var re = new RegExp('\\b' + _stripDiacritics(term), 'ig');
        var _esc = Utils.escapeMarkup;

        var match;
        var lastindex=0;
        var out = '';

        var _text = _stripDiacritics(text);

        while ((match = re.exec(_text)) !== null) {
            out += _esc(text.substring(lastindex, match.index));
            out += '<strong>' + _esc(match[0]) + '</strong>';
            lastindex = re.lastIndex;
        }
        out += _esc(text.substr(lastindex));

        return out;
    };

    CachingAjaxAdapter.prototype.matches = function (params, data) {
        // mostly copy/paste from upstream

        var _matcher = CachingAjaxAdapter.prototype.matches;

        // Always return the object if there is nothing to compare
        if ($.trim(params.term) === '') {
            return data;
        }

        // Do a recursive check for options with children
        if (data.children && data.children.length > 0) {
            // Clone the data object if there are children
            // This is required as we modify the object to remove any non-matches
            var match = $.extend(true, {}, data);

            // Check each child of the option
            for (var c = data.children.length - 1; c >= 0; c--) {
                var child = data.children[c];

                var matches = _matcher(params, child);

                // If there wasn't a match, remove the object in the array
                if (matches == null) {
                    match.children.splice(c, 1);
                }
            }

            // If any children matched, return the new object
            if (match.children.length > 0) {
                return match;
            }

            // If there were no matching children, check just the plain object
            return _matcher(params, match);
        }

        var original = _stripDiacritics(data.text);
        var term = _stripDiacritics(params.term);

        // Check if the text contains the term
        if (new RegExp('\\b' + term, 'i').test(original)) {
                return data;
        }

        // If it doesn't contain the term, don't return anything
        return null;
    };

    CachingAjaxAdapter.prototype._getDefaults = function () {
        // default options

        return {
            // use infinite scrolling even without the ajax machinery
            resultsAdapter: CustomResults,

            templateSelection: function (item) {
                return '' +
                    Utils.escapeMarkup(item.text) +
                    ' <sup class="badge">' + item.count + '</sup>';
            },

            __placeholder: ""
        };
    };

/*
  SingleSelection.prototype.display = function (data, container) {
    var template = this.options.get('templateSelection');
    var escapeMarkup = this.options.get('escapeMarkup');

    return escapeMarkup(template(data, container));
  };
*/

    CachingAjaxAdapter.prototype._applyDefaults = function (options) {
        // ajax defaults, that is

        options = CachingAjaxAdapter.__super__._applyDefaults(options);

        var defaults = {
            delay: 200,
            dataType: 'json',

            data: function (params) {
                console.log(params);
                return $.extend({}, params, {
                    search: params.term || "",
                    page: params.page || 1
                });
            },

            /*
            transport: function (params, success, failure) {
                var $request = $.ajax(params);

                $request.then(success);
                $request.fail(failure);

                return $request;
            },
             */

            __placeholder: ""
        };

        return $.extend({},
                        CachingAjaxAdapter.__super__._applyDefaults({}),
                        defaults, options, true);
    };

    CachingAjaxAdapter.prototype.query = function (params, callback) {
        // ensure everything has access to the current query term
        this.$element._term = params.term;

        var _Adapter;
        if (!params.term || params.term.length < 2) //TODO
            _Adapter = ArrayAdapter;
        else
            _Adapter = AjaxAdapter;

        var _query = Utils.bind(_Adapter.prototype.query, this);
        return _query(params, callback);
    };

    CachingAjaxAdapter.prototype.processResults = function (data, params) {
        // select2 needs id, text keys
        data.results = $.map(data.results, function (result) {
            return {
                id: result.item,
                text: result.item,
                count: result.count
            };
        });

        // there's more results when the backend sends a next page url
        data['pagination'] = {
            more: Boolean(data['next'])
        };

        return data;
    };
});


    $('[data-filter]').on('click', function() {
        target = $(this).data('filter');
        target = $(target);
        $(this).toggleClass('active');

        if (target.attr('disabled')) {
            target.removeAttr('disabled');
        } else {
            target.attr('disabled', true);
        }
    });

    // set initial history entry
    if (!history.state && Modernizr.history) {
        var data = $('.search-form').serialize();
        history.replaceState({
            data: data,
            tag: 'ecolex'
        }, '', '?' + data);
    }

    // reload results when the back button was pressed
    $(window).on("popstate", function(e) {
        // history states are tagged in order to ignore popstate events
        // triggered on page load.
        if (!history.state || history.state.tag !== "ecolex") {
            return;
        }
        $(".search-form").deserialize(history.state.data);
        submit(history.state.data);
    });

    // initial form value
    var _initial_form_data = $('.search-form').serialize();

    function debounce(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this,
                args = arguments;
            var later = function() {
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
        return debounce(function() {
            _push_and_submit(ajax);
        }, 500)();
    }

    function _push_and_submit(ajax) {
        if (ajax) {
            var data = $('.search-form').serialize();
            if (Modernizr.history) {
              history.pushState({
                  data: data,
                  tag: 'ecolex'
              }, '', '?' + data);
            }
            submit(data);
        } else {
            $('.search-form').submit();
        }
    }

    function block_ui() {
        $('.tooltip').remove();
        $('main').block({
            message: '<img src="/static/img/ajax-spinner.gif" width="48" height="48"><h3 style="color: #666; margin: 0;">Updating results<h3>',
            centerY: false,
            css: {
                padding: '0',
                margin: '0',
                border: '0',
                top: '169px',
                color: "#666",
                backgroundColor: 'transparent'
            },
            overlayCSS: {
                backgroundColor: '#ccc',
                opacity: 0.9
            }
        });
    }

    function unblock_ui() {
        $('main').unblock();
    }

    function is_changed(serialized_form_data) {
        if (serialized_form_data != _initial_form_data) {
            return true;
        }
        return false;
    }

    function submit(serialized_form_data) {
        if (is_changed(serialized_form_data)) {
            block_ui();
            $.ajax({
                url: '/result/ajax/?' + serialized_form_data,
                format: 'JSON',
                success: function(data) {
                    $('#layout-main').html(data.main);
                    $('#filters').html(data.sidebar);
                    $("#search-form-inputs").html(data.form_inputs);
                    _initial_form_data = serialized_form_data;
                    $(".search-form").deserialize(serialized_form_data);
                    get_select_facets();
                    // for bootstrap tour
                    $("body").trigger('onajax');
                },
                error: function(e) {
                    unblock_ui();
                }
            });
        } else {
            console.log('No new data, not submitting.');
        }
    }

    function get_select_facets() {
        if ($('.tag-options').length > 0) {
            var data = $('.search-form').serialize();

            $.ajax({
                url: '/facets/ajax/?' + data,
                format: 'JSON',
                success: function(data) {
                    for (var k in data) {
                        $('#' + k + '-filter select').html(data[k]);
                    }
                    init_all();
                    unblock_ui();
                }
            });

        }
    }

    function _process_facet_data(data) {
        var processed = [];
        $.each(data, function(item, count) {

            processed.push({
                id: item,
                text: item,
                count: count
            });
        });
        return processed;
    }


    function init_all() {
        $('.selection-facet').each(function(idx) {
            var self = $(this);
            var data = _process_facet_data(self.data('data'));
            // strip away the initial data, for performance reasons
            self.removeData('data');
            self.removeAttr('data-data');

            $(this).select2({
                data: data,
                dataAdapter: CachingAjaxAdapter
            });
        });



        // initialize tooltips
        // bootstrap tooltips are opt-in
        $('[data-toggle="tooltip"]').tooltip();

        // prevent disabled pagination anchor to trigger page reload
        $('.pagination').on('click', '.disabled', function(e) {
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

                push_and_submit(true);
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

            $("#slider-years").slider('setValue', [min, max]);
        };

        $('.filter-type button').click(function(e) {
            var current = $('#id_type').val() || [];
            var toggle_value = $(this).data('value');
            var is_homepage = $(this).parents().hasClass('homepage');
            if (current.indexOf(toggle_value) == -1) {
                current = [toggle_value];
            } else {
                current = [];
            }
            $('#id_type').val(current);
            // submit now for now
            if (is_homepage)
                push_and_submit(false);
            else
                push_and_submit(true);
        });

        // Treaty -> Type of Document/Field of application filter
        // COP Decision -> Decision Type, Decision Status /Decision Treaty
        $('input[type=checkbox]',
                $('.filter-decision, .filter-treaty, .filter-literature, .filter-global, .filter-legislation'))
            .change(function(e) {
                var current = [];
                var formid_elem = $(this).closest('[data-formid]');
                var form_id = formid_elem.data('formid');
                var value = $(this).val();
                if (value == 'AND' && $(this).is(':checked')) {
                    var target_id = $(this).data('target');
                    current.push('AND');
                }
                formid_elem.find('input:checked').each(function() {
                    current.push($(this).val());
                });
                $(form_id).val(current);
                // submit now for now
                if (form_id.indexOf("_op") > 0 && $(form_id.replace("_op", "")).val().length < 2) {
                    return;
                }
                push_and_submit(true);
            });

        // Year controls
        $('.global-filter input[type=number]').change(function(e) {
            $(this).focus();
        });

        $('.global-filter input[type=number]').on('blur', function(e) {
            var form_id = $(this).data('formid');
            $(form_id).val($(this).val());
            // submit le form
            push_and_submit(true);
        });

        // Lose focus on enter on number inputs
        $('input[type=number]').keypress(function(e) {
            var key = e.which;
            if (key == 13) // the enter key code
            {
                $(this).blur();
                return false;
            }
        });

        // Sortby controls
        $('.sortby').click(function(e) {
            e.preventDefault();
            var value = $(this).data('sortby');
            $('#id_sortby').val(value);
            push_and_submit(true);
        });

        $('button[type=submit]').off("click").on("click", function(e) {
            e.preventDefault();
            var is_homepage = $(this).parents().hasClass('homepage');
            if (is_homepage)
                push_and_submit(false);
            else
                push_and_submit(true);
        });

        $('#suggestion-link').click(function(e) {
            e.preventDefault();
            var value = $(this).text();
            $('#search').val(value);
            push_and_submit(true);
        });

        // Global reset button
        $('input[type=reset]').click(function(e) {
            e.preventDefault();
            var data = {
                'q': $('#search').val()
            };
            $('.search-form select, .search-form input').each(function() {
                $(this).val('');
            });
            $('#search').val(data.q);

            push_and_submit(true);
        });

        //Multiple select facet reset button
        $('button.reset-multiple').on("click", function(e) {
            var target = $(this).data('target');
            $('select' + target).each(function() {
                $(this).val('');
            });
            var tag_selector = 'input.tm-input[data-formid="' + target + '"]';
            $(tag_selector).tagsManager('empty');
            push_and_submit(true);
        });

        // Tag manager
        var substringMatcher = function(strs, regex_prefix) {
            return function findMatches(q, cb) {
                var matches, substrRegex;
                // an array that will be populated with substring matches
                matches = [];

                // regex used to determine if a string contains the substring `q`
                substrRegex = new RegExp(regex_prefix + q, 'i');

                // iterate through the pool of strings and for any string that
                // contains the substring `q`, add it to the `matches` array
                $.each(strs, function(i, str) {
                    if (substrRegex.test(str)) {
                        // the typeahead jQuery plugin expects suggestions to a
                        // JavaScript object, refer to typeahead docs for more info
                        matches.push({
                            'value': str
                        });
                    }
                });

                cb(matches);
            };
        };


        var tagValidator = function(strs) {
            return function(tag) {
                return (strs.indexOf(tag) !== -1);
            };
        };

        $(".tag-select").each(function() {
            var suggestions = [];
            var preselected = [];

            $(".tag-options option", this).each(function(i, opt) {
                var selected = $(opt).attr("selected");
                var entry = $(opt).text();
                if (selected)
                    preselected.push(entry);
                suggestions.push(entry);
            });

            function get_values(tags, options) {
                var result = [];
                var fixed_tags = {};
                options.each(function() {
                    text = $(this).text();
                    val = $(this).val();
                    fixed_tags[text] = val;
                });

                for (var j = 0; j < tags.length; j++) {
                    var tag = tags[j];
                    tag = fixed_tags[tag];
                    result.push(tag);
                }
                return result;
            }

            $('.tm-input', this).each(function() {
                var self = this;
                var options = $('option', $(this).parents('.tag-select').children('.tag-options')[0]);

                $(this).tagsManager({
                    delimiters: [9, 13],
                    tagsContainer: $('<ul/>', {
                        class: 'tm-taglist'
                    }),
                    tagCloseIcon: '',
                    prefilled: preselected,
                    validator: tagValidator(suggestions),
                    deleteTagsOnBackspace: false,
                    CapitalizeFirstLetter: false,
                    onlyTagList: true
                }).on("tm:spliced", function(e) {
                    var formid = $(this).data('formid');
                    var value = $(this).tagsManager('tags');
                    $(formid).val(get_values(value, options));
                    push_and_submit(true);
                }).on("tm:pushed", function(e) {
                    var formid = $(this).data('formid');
                    var value = $(this).tagsManager('tags');
                    $(formid).val(get_values(value, options));
                    push_and_submit(true);
                }).bind('typeahead:selected', function(e, v, r) {
                    $(this).tagsManager('pushTag', v.value);
                    $(this).blur();
                });

                $(this).wrap($('<div/>', {
                    class: 'tm-wrapper'
                }));

                labelFor = $(this).attr('data-formid');
                labelFor = labelFor.substr(1, labelFor.length); // remove #
                label = $('<label/>', {
                    'class': 'tm-label',
                    'for': labelFor
                });
                $(this).before(label);
                $(self).on("focus", function(e) {
                    var ev = $.Event("keydown");
                    ev.keyCode = ev.which = 40;
                    $(self).trigger(ev);
                    return true;
                });

                $(label).on("click", function(e) {
                    $(self).focus();
                    return true;
                });

                var regex_prefix = '^';
                if ($(this).hasClass('full-match')) {
                    regex_prefix = '';
                }
                else if ($(this).hasClass('word-match')) {
                    regex_prefix = '\\b';
                }

                suggestions = suggestions.filter(function(item) {
                    return preselected.indexOf(item) === -1;
                });

                // console.log(suggestions);


                $(this).typeahead({
                    hint: false,
                    highlight: true,
                    minLength: 0
                }, {
                    name: 'states',
                    displayKey: 'value',
                    source: substringMatcher(suggestions, regex_prefix)
                });

                $(this).on('blur', function() {
                    $(this).val('');
                });

            });
        });

    }

    if ($('.search-form').hasClass('homepage')) {
        init_all();
    } else {
        get_select_facets();
    }
});
