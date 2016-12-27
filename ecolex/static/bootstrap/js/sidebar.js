(function($) {
    $(document).ready(function() {

        $languagetest = $(".dropdown");
        $notFiltered = $("#not-filtered");
        $filtered = $("#filtered");
        $body = $("body");
        $filters = $('#filters');
        $backdrop = $('#backdrop');
        $filterTrigger = $('#filter-trigger');
        $results = $('#results');

        $languagetest.click(function() {
            return true;
        });

        $filterTrigger.click(function() {
            $filters.addClass('open');
            $body.addClass("sidebaropen");
        });

        $backdrop.on('click', function() {

            $filters.removeClass('open');
            $body.removeClass('sidebaropen');
        });

        $('.dropdown-toggle').on('click', function() {
            $('.dropdown-menu').animate({
                height: 'toggle'
            }, 200);
        })




        if (window.matchMedia("(max-width: 480px)").matches) {
            $('#participants a').removeClass('btn-link').removeClass('pull-right').addClass('btn-default').css('display', 'block');
              
              if($('html').attr('lang') == 'fr'){
                $('.search-form input').attr('placeholder', 'Rechercher');
              }
              else if ($('html').attr('lang') == 'es'){
                 $('.search-form input').attr('placeholder', 'Buscar');
              }
              else {
                $('.search-form input').attr('placeholder', 'Search');
              }
        }

      if (window.matchMedia("(max-width: 768px)").matches) {
        var search_form_width = $('.search-form .button-control').width();
        $('#query-remove').css('right',search_form_width+'px');
      }


        $('.navbar button').on('click', function() {
            $(this).toggleClass('button-triggered')
        })


        //TODO find a way that doesn't depend on the link structure
        templink = $(location).attr('href');
        query = window.location.href.split('/').pop();

        if (query && query !== '?q=' && query !== '?q=&xdate_min=&xdate_max=') {
            // filtered
            $notFiltered.addClass('hidden');
            $filtered.removeClass('hidden');
        } else {
            // not filtered
            $notFiltered.removeClass('hidden');
            $filtered.addClass('hidden');
        }
    });

}(jQuery));
