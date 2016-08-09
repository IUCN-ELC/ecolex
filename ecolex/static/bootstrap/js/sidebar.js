(function ($) {
  $(document).ready(function () {

    $languagetest= $(".dropdown");
    $notFiltered = $("#not-filtered");
    $filtered= $("#filtered");
    $body = $("body");
    $filters = $('#filters');
    $backdrop = $('#backdrop');
    $filterTrigger = $('#filter-trigger');
    $results = $('#results');

  $languagetest.click(function(){
    return true;
  });

    $filterTrigger.click(function () {
      $filters.addClass('open');
      $body.addClass("sidebaropen");
    });

    $backdrop.on('click', function () {
        
        $filters.removeClass('open');
        $body.removeClass('sidebaropen');
    });

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

} (jQuery));
