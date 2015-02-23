// Bootstrap tour
var _templateHelp = "<div class='popover-help'><button class='no-btn pull-right' data-role='end'>End tour</button><strong><span data-role='current'></span>/<span data-role='steps'></span></strong></div>",
    _templateNav = "<div class='popover-navigation'><button class='btn btn-sm btn-default' data-role='next'>Continue</button></div>",
    _templateStart = "<div class='popover-navigation clearfix'><button class='btn btn-success btn-sm col-xs-6' data-role='next'>Start tour</button><button class='btn btn-sm btn-link col-xs-6' style='color: #aaa' data-role='end'>No, thanks!</button></div>",
    _templateEnd = "<div class='popover-navigation text-center'><button class='btn btn-success' data-role='end'>End tour</button></div>";
var templateNoNav = "<div class='popover tour'><div class='arrow'></div>" + _templateHelp + "<h3 class='popover-title'></h3><div class='popover-content'></div></div>",
    templateStart = "<div class='popover tour'><div class='arrow'></div><h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateStart + "</div>",
    templateEnd = "<div class='popover tour'><div class='arrow'></div><h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateEnd + "</div>",
    templateDefault = "<div class='popover tour'><div class='arrow'></div>" + _templateHelp + "<h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateNav + "</div>";

var tourSteps = [
  // Welcome
  {
    orphan: true,
    title: "Take a tour of the prototype",
    content: "See all the great features of this <strong>prototype</strong> and learn about the thing we have in mind for the final product.",
    template: templateStart,
    onNext: function() {
      str = "Access to Genetic Resourses";
      $("#search").val(str);
    }
  },
  // The search bar
  {
    element: "#search",
    placement: "bottom",
    title: "Permanent search bar",
    content: "<p>Always visible from any page. Provides <strong>quick access</strong> to the website's main function.</p><p>We'll start by searching for <em>Access to Genetic Resourses</em>.</p>"
  },

  // Speed
  // {
  //   element: "#number-of-results",
  //   placement: "bottom",
  //   title: "Search results",
  //   content: "We just found 7594 results for 'Access to Genetic Resourses' in less than 1 second. "
  // }

  // Interactive categories
  {
    path: "/result/?q=Access+to+Genetic+Resourses",
    element: ".btn-group.filter-type",
    placement: "right",
    title: "Interactive categories",
    content: "<p>Currently, we are looking at records from all categories. However, you can search in <strong>any number of categories simultaneously</strong>.</p><p>For instance: 'Legislation' and 'Court decisions' don't need separate windows.</p>"
  },
  // Highlighted results 
  {
    element: ".search-result:first-child .search-result-title a",
    placement: "right",
    title: "Highlighted results",
    content: "<p>Every matched word is in bold, like <em>Access to genetic</em>, but not <em>resourses</em>. That's because 'resources' is spelled wrong.</p>"
  },
  // The suggestions
  {
    element: "#suggestion em",
    placement: "right",
    title: "Resour<strong>c</strong>es, not Resour<strong>s</strong>es!",
    content: "<p><strong>Spelling corrections</strong> lead to more relevant results and a better user experience.</p><div class='popover-hint'>Click the suggested text!</div>",
    template: templateNoNav,
    onShow: function(tour) {
      $('body').on('onajax', function() {
        if (tour.getCurrentStep() < 6) {
          tour.next();
          
        }
      });
    }
  },
  // The result relevance
  {
    element: ".search-result:first-child .hl:first-child",
    placement: "top",
    title: "Relevant results",
    content: "<p><strong>Access to Genetic Resourses</strong> matches perfectly and therefor is first.</p><p><a href='http://ecolex.org'>ecolex.org</a> currently uses a <em>Match all/Match any of these words</em> setting that is very difficult to use.</p>",
  },
  // Filters
  {
    element: "#filters",
    placement: "top",
    title: "Why are category filters hidden?",
    content: "<p>Because no category was selected. The reason is&hellip;</p>",
    onNext: function() {
      $('.btn[data-value="treaty"]').click();
    }
  },
  // Contextual filters
  {
    element: "#filters",
    placement: "top",
    title: "Contextual filters",
    content: "<p>Filters are opened automatically when you select between one or more categories.</p><p><strong>Smart interfaces anticipate and react to user's behaviour.</strong></p>",
  },
  // The content types
  {
    element: "#filters",
    placement: "left",
    title: "Faceted navigation",
    content: "<p>Try it yourself:</p><ol><li>Look for <strong>multilateral</strong> treaties</li><li>Add <strong>Waste management</strong> as a keyword</li><li>Only show records <strong>after 1900</strong></li></ol>",
  },
  // The details page
  {
    path: "/details/a70ca280-b336-4fbb-b8f5-be390074c1ce/",
    element: ".record-title",
    placement: "top",
    title: "The details page",
    content: "Designed to emphasize structure and readibility."
  },
  // Participants
  {
    element: "#participants",
    placement: "top",
    title: "Unobtrusive Participants Table",
    content: "Of <strong>2141</strong> treaties, only <strong>473</strong> have more than <strong>5</strong> participants.<br>Since not all users analyze this table, we have redesigned it to be more discreet.However&hellip;"
  },
  // Extras on demand
  {
    element: "#participants-extras",
    placement: "left",
    title: "Extras on demand",
    content: "We have a separate view for the users that want to examine this section in detail."
  },
  // References
  {
    element: "#treaty-references",
    placement: "top",
    title: "Treaty references",
    content: "For the finished product, we wish to draw a graphic timeline of the treaty references.<br>NOT in the prototype."
  },
  // References
  {
    orphan: true,
    title: "Beyond the prototype",
    content: "<p>Please keep in mind that this is a prototype and that some features are not included.</p><p><strong>More suggestions for improving Ecolex</strong> can be found in the <em>Technical description</em>.</p>",
  },
  // Cross-device
  {
    orphan: true,
    title: "Mobile &amp; Tablet support",
    content: "Please have a look at this prototype from your mobile or tablet as well.",
    template: templateEnd
  }
];

var tour = new Tour({
  name: "tour",
  animation: true,
  keyboard: false,
  template: templateDefault,
  onShown: function(tour) {
    $('.popover-help [data-role="current"]').text(tour.getCurrentStep());
    $('.popover-help [data-role="steps"]').text(tourSteps.length - 1);
  },
  steps: tourSteps,
  debug: true,
  // backdrop: true,
  onStart: function() {
    console.log('Start');
  }
});

$(document).ready(function() {

  
  if (!tour.ended()) {
    tour.init();
  }

  tour.start();
  // Start
  if ($('#welcome-text').length && tour.ended()) {
    tour.restart();
  }

  $('#suggestion-link').on('click', function() {
    $('.popover.tour-tour').hide();
  });

  // tour.start();

  // if (tour.ended()) {
  //   // decide what to do
  //   tour.restart();
  // }
});
