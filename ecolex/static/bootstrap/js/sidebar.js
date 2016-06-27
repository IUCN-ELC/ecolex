

(function ($) {

    $(document).ready(function () {

        $body = $("body");
        $filters = $('#filters');
        $backdrop = $('#backdrop');
        $filterTrigger = $('#filter-trigger');
        $results = $('#results');
        // $last=$filters.lastChild;
        $filterTrigger.click(function () {
            console.log('opening sidebar');
            // event.stopPropagation();
            $filters.addClass('open');
            $body.addClass("sidebaropen");
        });

        $backdrop.on('click', function () {
            console.log('closing sidebar');
            $filters.removeClass('open');
            $body.removeClass('sidebaropen');
        });


$templink = $(location).attr('href'); 



        if (window.location.href.indexOf("?q=") > -1) {
            $results.addClass('shown')
        }


        if(($templink.slice(-23))==("=&xdate_min=&xdate_max=")) {
            $results.removeClass('shown')
         
        }



        /*
        
         $body = $("body");
        $body.click(function() {
        console.log("sdsd");
        
        });
        
        
             function showValues() {
            var fields = $( ":input" ).serializeArray();
            // $( "#results" ).empty();
            jQuery.each( fields, function( i, field ) {
             
             if((field.value!=" ")&&(field.value != null)){
              $("#results").append( "<li>" + field.value + " " + "</li>") ;
        }
        
        
        // $('results').find('<li>').each(function(){
        //     if($(this)==" ")
        //         $(this).remove();
        // });
        
        
        
        
            });
          }
         
          $( ":checkbox, :radio" ).click( showValues );
          $( "select" ).change( showValues );
          showValues();
        */














    });

} (jQuery));