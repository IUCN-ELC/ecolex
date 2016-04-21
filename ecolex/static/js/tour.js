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
  {
    orphan: true,
    title: "Welcome to the tour",
    content: "<p>Please follow the tour to the end. It only takes 5 minutes.</p>"
  },
  // The search bar
  {
    element: "#search",
    placement: "bottom",
    title: "Permanent search bar",
    content: "<p>Always visible from any page. Provides <strong>quick access</strong> to the website's main function.</p><p>We'll start by searching for <em>Access to Genetic Resourses</em>.</p>",
    onShow: function() {
      str = "Access to Genetic Resourses";
      $("#search").val(str);
    }
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
    path: "/en/result/?q=Access+to+Genetic+Resourses&yearmin=&yearmax=&sortby=",
    element: ".btn-group.filter-type",
    placement: "right",
    title: "Interactive categories",
    content: "<p>This approach allows you to filter results from more than category, meaning you can search for Treaties and COP Decisions simultaneously.</p>"
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
    content: "<p>A smart search engine doesn't rely on <em>Match all/Match any these Words</em>. For example, <em>Access to Genetic Resources</em> matches perfectly and is therefor first in the list of results.</p><p>For details regarding relevancy, check the Technical description document.</p>"
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
    onNext: function(tour) {
      var nextUrl = $('.result-links').eq(0).attr('href')
      var nextStep = tour.getCurrentStep() + 1;
      tour._options['steps'][nextStep]['path'] = nextUrl;
    }
  },
  // The details page
  {
    element: ".record-title",
    placement: "top",
    title: "The details page",
    content: "Designed to emphasize structure and readibility.",
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
    content: "<p>This prototype offers an improved search and filter engine.  To reach the mature envisioned application more features need to be added.</p><p><strong>More suggestions for improving Ecolex</strong> can be found in the <em>Technical description</em>.</p>",
  },
  // Cross-device
  {
    path: "/en/",
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
  storage: false,
  template: templateDefault,
  onShown: function(tour) {
    $('.popover-help [data-role="current"]').text(tour.getCurrentStep() + 1);
    $('.popover-help [data-role="steps"]').text(tourSteps.length);
  },
  steps: tourSteps,
});

$(document).ready(function() {


  if (!tour.ended()) {
    tour.init();
  }

  $('#suggestion-link').on('click', function() {
    $('.popover.tour-tour').hide();
  });

  $('[data-toggle="tour"]').on('click', function() {
    tour.restart();
  });

});
