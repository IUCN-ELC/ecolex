$(document).ready(function() {

var S2U = $.fn.select2.amd.require('select2/utils');

var _DIACRITICS = $.fn.select2.amd.require('select2/diacritics');
function _stripDiacritics (text) {
    // courtesy of upstream
    function match(a) {
        return _DIACRITICS[a] || a;
    }
    return text.replace(/[^\u0000-\u007E]/g, match);
};

RegExp.__escape_re = /[-\/\\^$*+?.()|[\]{}]/g;
RegExp.escape = function(s) {
    return s.replace(RegExp.__escape_re, '\\$&');
};

/* debugbugbugbug * /
var _obs_trigger = S2U.Observable.prototype.trigger;
S2U.Observable.prototype.trigger = function (event) {
    if (['enable', 'blur', 'close', 'closing', 'focus',
         'toggle', 'open', 'opening', 'keypress',
         'results:focus'
        ].indexOf(event) === -1)
        console.log('[ev]', event, '[lx]', this.listeners[event]);

    _obs_trigger.apply(this, arguments);
};
// */

/* our custom select2 adapter */
$.fn.select2.amd.define('ecolex/select2/adapter', [
    'select2/utils',
    'select2/data/array',
    'select2/data/ajax',
    'select2/selection/search',
    'select2/results',
    'select2/dropdown/infiniteScroll',
    'select2/selection/multiple',
    'select2/selection/placeholder'
], function (
    Utils,
    ArrayAdapter, AjaxAdapter,
    Search,
    Results, InfiniteScroll,
    MultipleSelection, Placeholder) {

    /***/
    var CustomResults = Utils.Decorate(Results, InfiniteScroll);


    /* hacks, hacks, hacks */
    // prevent backspace in search field from affecting previous item
    Search.prototype.searchRemoveChoice = function() {
        return;
    };

    // prevent toggling on item removal. TODO: fix, it's ugly
    MultipleSelection.prototype.bind = function (container, $container) {
        // this is mostly copy/paste

        var self = this;

        MultipleSelection.__super__.bind.apply(this, arguments);

        // this part customized
        this.$selection.on('click', function (evt) {
            if ($(evt.target).is('input.select2-search__field')) {
                self.trigger('toggle', {
                    originalEvent: evt
                });
            }
        });
        // end custom

        this.$selection.on(
            'click',
            '.select2-selection__choice__remove',
            function (evt) {
                // Ignore the event if it is disabled
                if (self.options.get('disabled')) {
                    return;
                }

                var $remove = $(this);
                var $selection = $remove.parent();

                var data = $selection.data('data');

                self.trigger('unselect', {
                    originalEvent: evt,
                    data: data
                });
            }
        );
    };

    // don't remove placeholder on selection
    Placeholder.prototype.update = function (decorated, data) {
        var $placeholder = this.createPlaceholder(this.placeholder);
        this.$selection.find('.select2-selection__rendered').append($placeholder);
        return decorated.call(this, data);
    };

    /* the thing */
    var CachingAjaxAdapter = function ($element, options) {
        $.extend(options.options, {
            // hardcode our customized results adapter
            resultsAdapter: CustomResults,
            // make sure the template has access to our stuff
            templateResult: this.templateResult.bind(this),
            // the same with the selection template
            templateSelection: this.templateSelection.bind(this),
            // no point defining this in options
            escapeMarkup: function (txt) { return txt; }
        });

        CachingAjaxAdapter.__super__.constructor.call(this, $element, options);
    };

    Utils.Extend(CachingAjaxAdapter, AjaxAdapter);

    CachingAjaxAdapter.prototype.templateResult = function (result, container) {
        // .loading means this item is the "loading" message
        if (result.loading) return result.text;

        var term = this._term;
        var text = this._highlight(result.text, term);

        return '' +
            '<div class="clearfix">' +
              '<div class="pull-right">' + result.count + '</div>' +
              '<div>' + text + '</div>' +
            '</div>';
    };

    CachingAjaxAdapter.prototype._highlight = function (text, term) {
        // this has to do both highlighting and escaping
        // TODO: make the preparation code not run once for every list item.
        // (needs some hacking of select2(?))
        var term = $.trim(term);
        var _esc = Utils.escapeMarkup;

        if (term === '') return _esc(text);

        var _text = _stripDiacritics(text);
        var words = RegExp.escape(_stripDiacritics(term)).split(/ +/);
        var matches = [];

        $.each(words, function(idx, word) {
            var re = new RegExp('\\b' + word, 'ig');
            var match;
            //var lastindex=0;

            while ((match = re.exec(_text)) !== null) {
                matches.push({
                    index: match.index,
                    length: match[0].length
                });
                //lastindex = re.lastIndex
            }
        });

        // sort the matches by index.
        var _overlaps = false;
        matches.sort(function(m1, m2) {
            var diff = m1.index - m2.index;
            if (diff === 0) {
                // we have an overlapping match, make the longest match first
                _overlaps = true;
                return m2.length - m1.length;
            }
            return diff;
        });

        if (_overlaps) {
            var _match, _oldindex, _index;
            // iterate them backwardsly to preserve longer match
            for (var i = matches.length -1; i >= 0 ; i--) {
                _match = matches[i];
                _index = _match.index;
                if (_index == _oldindex) {
                    // if duplicate, pop previous item
                    matches.splice(i+1, 1);
                }
                _oldindex = _index;
            }
        }

        var out = "";
        var lastindex=0;
        var match;

        for (var i = 0, j =  matches.length; i < j ; i++) {
            match = matches[i];

            out += _esc(text.substring(lastindex, match.index));

            out += '<strong>';
            out += _esc(text.substr(match.index, match.length));
            out += '</strong>';

            lastindex = match.index + match.length;
        }
        out += _esc(text.substr(lastindex));

        return out;
    };

    CachingAjaxAdapter.prototype.templateSelection = function (data, container) {
        return '' +
            Utils.escapeMarkup(data.text) +
            '&nbsp;' + // non breaking space
            '<span class="select2-selection__choice__count">' +
                (data.count !== undefined ? data.count : '0') +
            '</span>';
    };

    CachingAjaxAdapter.prototype.matches = function (params, data) {
        // mostly copy/paste from upstream

        var term = $.trim(params.term);

        // Always return the object if there is nothing to compare
        if (term === '') {
            return data;
        }

        var _matcher = CachingAjaxAdapter.prototype.matches;

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

        // end copy paste. this is the differing part.
        var txt = _stripDiacritics(data.text);
        var words = RegExp.escape(_stripDiacritics(term)).split(/ +/);

        var matches = true;
        $.each(words, function(idx, word) {
            if (new RegExp('\\b' + word, 'i').test(txt)) {
                return true;
            } else {
                matches = false;
                return false;
            }
        });

        if (matches) return data;

        // If it doesn't contain the term, don't return anything
        return null;
    };

    CachingAjaxAdapter.prototype._applyDefaults = function (options) {
        // ajax defaults, that is

        var defaults = {
            delay: 200,
            dataType: 'json',

            data: function (params) {
                // api-specific params
                var base_params = {
                    search: params.term || "",
                    page: params.page || 1
                };

                // send allong all form fields
                //var _form_data = $(this[0].form).serializeArray();
                var _form_data = this[0].form._form_data;

                var form_params = {};
                $.each(_form_data, function(idx, obj) {
                    // courtesy of
                    // http://benalman.com/projects/jquery-misc-plugins/#serializeobject

                    var n = obj.name,
                        v = obj.value;

                    form_params[n] = form_params[n] === undefined ? v
                        : $.isArray( form_params[n] ) ? form_params[n].concat( v )
                        : [ form_params[n], v ];
                });

                return $.extend(
                    {}, form_params, base_params);//, params);
            }
/*
            ,

            // just for debugging
            transport: function (params, success, failure) {
                console.log('[ajax]', params.url, params.data);

                var $request = $.ajax(params);

                $request.then(success);
                $request.fail(failure);

                return $request;
            }
 */
        };

        return $.extend({},
                        CachingAjaxAdapter.__super__._applyDefaults({}),
                        defaults, options);
    };

    CachingAjaxAdapter.prototype.hasMoreData = function (params) {
        // we have more data when:
        //   - the data was template-provided and
        //   - there is an ajax url and
        //   - the template said there's more data.
        // or when:
        //   - the data was ajax-provided and
        //   - the backend said so.

        if (!this.ajaxOptions.url ||
            !this.options.get('more')
           )
            return false;

        if (params &&
            (params.term ||
             (params.page && params.page > 1)
            )
           )
            return true;

        return false;
    };

    CachingAjaxAdapter.prototype._default_query = function (params, callback) {
        // wrapper around the default SelectAdapter.prototype.query
        // that lets us add pagination info

        //console.log(':: query :: default');

        var _super_query = ArrayAdapter.prototype.query;
        var wrapper = callback;

        if (this.options.get('more')) {
            wrapper = function(data) {
                data.pagination = {more: true};
                callback(data);
            };
        }

        _super_query.call(this, params, wrapper);

    };

    CachingAjaxAdapter.prototype._cached_query = function(params, callback) {
        // applies the default matching logic against the cached data

        //console.log(':: query :: cached');

        var results = [];
        var self = this;

        $.each(this._cached_data.data.results, function(idx, result) {
            if (self.matches(params, result) !== null)
                results.push(result);
        });

        callback({
            results: results
        });
    };

    CachingAjaxAdapter.prototype._ajax_query = function (params, callback) {
        //console.log(':: query :: ajax');

        // TODO: fix bug:
        // items are doubled in results when they're aleady selected

        AjaxAdapter.prototype.query.call(this, params, callback);
    };

    CachingAjaxAdapter.prototype.query = function (params, callback) {
        // ensure everything has access to the current query term
        this._term = params.term;

        if (this._cached_data && this.isSubQuery(params))
            return this._cached_query(params, callback);
        else if (this.hasMoreData(params))
            return this._ajax_query(params, callback);
        else
            return this._default_query(params, callback);

    };

    CachingAjaxAdapter._processData = function (data, selected) {
        if (data === '""') return [];
        $.each(data, function(idx, item) {
            item._key = item.id;
            item.id = item.text;
            item.selected = selected && $.inArray(item.text, selected) != -1;
        });
    };

    CachingAjaxAdapter.prototype.processResults = function (data, params) {
        CachingAjaxAdapter._processData(data.results);

        // there are more results when the backend sends a next page url
        var more = Boolean(data['next']);

        if (more) {
            // tell the default ajax adapter to request the next page
            data['pagination'] = {
                more: more
            };
        } else {
            // cache things
            this.setCachedData(data, params);
        }

        return data;
    };

    CachingAjaxAdapter.prototype.setCachedData = function (data, params) {
        // cache the current term and the current data if there's only
        // one page, and this is not a sub-query of the previous search
        if ((params.page && params.page > 1) ||
            this.isSubQuery(params)
           )
            return;

        this._cached_data = {
            term: params.term || "",
            data: data
        };
    };

    CachingAjaxAdapter.prototype.isSubQuery = function(params) {
        if (!this._cached_data)
            return false;

        var term = params.term || "";
        var cached_term = this._cached_data.term;

        return (cached_term == "" ||
                term.indexOf(cached_term) === 0);
    };


    return CachingAjaxAdapter;
});


/* main */

    // set up select2

    var _DataAdapter = $.fn.select2.amd.require('ecolex/select2/adapter');

    $('.selection-facet').each(function(idx) {
        var self = $(this);
        var _data = self.data('data');
        _DataAdapter._processData(_data, self.data('selected'));
        // strip away the initial data, for performance reasons
        self.removeData('data');
        self.removeAttr('data-data');

        self.select2({
            data: _data,
            dataAdapter: _DataAdapter,
        });

        var search_field_id = self.attr('id') + '-search-field';
        var search_field = self.next().find('.select2-search__field');
        search_field.attr('id', search_field_id);
        self.change(submit);

        // add clearfix to select2 widget
        //self.next().addClass('clearfix');
    });

    // cache de current search data on the form
    var _form = $('#search-form');
    _form[0]._form_data = _form.serializeArray();


    /* old stuff re-enabled / temporarily adapted */

    function submit() {
        $('#search-form').submit();
    };

    // TODO: not the most beautiful approach this
    $('#search-form input:checkbox').change(submit);

    // Type facet controls
    $('.filter-type button').click(function(e) {
        var current = $('#id_type').val() || [];
        var toggle_value = $(this).data('value');
        var index = current.indexOf(toggle_value);

        if (index == -1) {
            current.push(toggle_value);
        } else {
            current.splice(index, 1);
        }

        $('#id_type').val(current);

        submit();
    });

    $('button.reset-multiple').click(function(e) {
        e.preventDefault();
        var target = $(this).data('target');
        $(target).select2('val', '');
    });

    $('button.reset-year').click(function(e) {
        e.preventDefault();
        $('#year-min').val('');
        $('#year-max').val('');
        submit();
    });

    // Reset query string
    $('#query-remove').click(function(e) {
        $('#search').val('');
        submit();
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

            // TODO: this is annoying
            submit();
        });

    // Global reset button
    $('input[type=reset]').click(function(e) {
        e.preventDefault();
        $form = $('#search-form');
        $form[0].reset();
        $('#search-form input:checkbox:checked').prop("checked", false);
        $('#search-form option:selected').prop("selected", false);
        $('#year-min').val('');
        $('#year-max').val('');
        $('#id_type option:selected').prop("selected", false);
        $form.submit();
    });

    /* end old stuff */

/*

// more commenting

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

*/


/*

// TODO: repair / re-enable this

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


*/

/*

 // ok ....


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


    function init_all() {


        // prevent disabled pagination anchor to trigger page reload
        $('.pagination').on('click', '.disabled', function(e) {
            e.preventDefault();
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

*/

});
