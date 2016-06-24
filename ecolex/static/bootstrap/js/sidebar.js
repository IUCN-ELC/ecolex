

(function ($) {

 $(document).ready(function(){

    $body = $("body");
    $filters = $('#filters');
    $backdrop = $('#backdrop');
    $filterTrigger = $('#filter-trigger');
    // $last=$filters.lastChild;
    $filterTrigger.click(function() {
        console.log('opening sidebar');
        // event.stopPropagation();
        $filters.addClass('open');
        $body.addClass("sidebaropen");
    });
    
    $backdrop.on('click', function() {
        console.log('closing sidebar');
        $filters.removeClass('open');
        $body.removeClass('sidebaropen');
    });

    

   


});

}(jQuery));