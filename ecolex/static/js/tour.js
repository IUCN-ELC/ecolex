// Bootstrap tour
var _templateHelp = "<div class='popover-help'><button class='no-btn pull-right' data-role='end'>End tour</button><strong><span data-role='current'></span>/<span data-role='steps'></span></strong></div>",
    _templateNav = "<div class='popover-navigation'><button class='btn btn-sm btn-default' data-role='next'>Next</button></div>",
    _templateStart = "<div class='popover-navigation clearfix'><button class='btn btn-success btn-sm col-xs-6' data-role='next'>Start tour</button><button class='btn btn-sm btn-link col-xs-6' style='color: #aaa' data-role='end'>No, thanks!</button></div>",
    _templateEnd = "<div class='popover-navigation text-center'><button class='btn btn-success' data-role='end'>End tour</button></div>";
var templateNoNav = "<div class='popover tour'><div class='arrow'></div>" + _templateHelp + "<h3 class='popover-title'></h3><div class='popover-content'></div></div>",
    templateStart = "<div class='popover tour'><div class='arrow'></div><h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateStart + "</div>",
    templateEnd = "<div class='popover tour'><div class='arrow'></div><h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateEnd + "</div>",
    templateDefault = "<div class='popover tour'><div class='arrow'></div>" + _templateHelp + "<h3 class='popover-title'></h3><div class='popover-content'></div>" + _templateNav + "</div>";

var tourSteps = [
  // Step 1: Welcome
  {
    orphan: true,
    title: "Welcome to ECOLEX",
    content: "<p>Please follow the tour to the end. It only takes 5 minutes.</p>"
  },
  // Step 2: The search bar
  {
    path: "/",
    element: "#search",
    placement: "bottom",
    title: "Permanent search bar",
    content: "<p>Always visible from any page. Provides <strong>quick access</strong> to the website's main function.</p><p>We'll start by searching for <em>Fishery conservation</em>.</p>",
    onShow: function() {
      $("#search").val("Fishery consrvation");
    }
  },
  // Step 3: Search suggestions
  {
    path: "/result/?q=Fishery+consrvation",
    element: "#suggestion em",
    placement: "right",
    title: "Oops, a typo!",
    content: "<p><strong>Spelling corrections</strong> lead to more relevant results and a better user experience.</p><div class='popover-hint'>Click on the suggested text!</div>",
    onNext: function() {
      // In case user presses Next and not the link
      if (document.location.href.indexOf('conservation') == -1) {
        document.location.href = '/result/?q=Fishery+conservation';
        return (new jQuery.Deferred()).promise();
      }
    }
  },
  // Step 4: Highlighted results
  {
    element: ".search-result:first-child .search-result-title a em:first-child",
    placement: "right",
    title: "Highlighted results",
    content: "<p>Every matched word is in bold, like <em>Conservation</em>.</p>",
  },
  // Step 5: Dataset links
  {
    element: ".btn-group.filter-type",
    placement: "right",
    title: "Multiple datasets",
    content: "<p>You may search within any combination of datasets.</p><p>Let's select treaties.</p>",
    onNext: function() {
      $("button[data-filter='#treaty-fieldset']").click();
    }
  },
  // Step 6: Sorting
  {
    element: "a.sortby:first-child",
    placement: "bottom",
    title: "Sorting results",
    content: "<p>When searching for a phrase, results are sorted by relevance.</p><p>You can also sort them by date.</p>"
  },
  // Step 7: Common filters
  {
    element: ".global-filter",
    placement: "left",
    title: "Filtering",
    content: "<p>You can obtain more specific results by applying filters.</p><p>Click on Geographical Area and select South America.</p><p>Try using the keyboard to search for values and ENTER to select them.</p>",
  },
  // Step 8: More filters
  {
    element: "#filter-treaties",
    placement: "left",
    title: "More filters",
    content: "<p>Each dataset has its own specific fields for filtering. They are shown or hidden when more datasets are selected.</p>",
    onNext: function(tour) {
      var nextUrl = $('.result-links').eq(0).attr('href')
      var nextStep = tour.getCurrentStep() + 1;
      tour._options['steps'][nextStep]['path'] = nextUrl;
    }
  },
  // Step 9: The details page
  {
    element: ".record-title",
    placement: "top",
    title: "The details page",
    content: "<p>The full display pages are designed to emphasize structure and readability.</p>",
  },
  // Step 10: Language picker
  {
    element: "#language-picker",
    placement: "left",
    title: "ECOLEX is multilingual",
    content: "<p>You can switch the language and translated content will be presented, where available.</p><p>Let's change to Spanish.</p>",
  },
  // Step 11: Spanish treaty
  {
    path: "/es/details/treaty/convention-on-the-conservation-and-management-of-fishery-resources-in-the-south-east-atlantic-ocean-seafo-tre-001384/",
    element: ".record-title",
    placement: "bottom",
    title: "The treaty title is now translated",
    content: "<p>And most of the other fields, as well.</p>",
  },
  // Step 12: Breadcrumbs
  {
    element: "main div.container a:first",
    placement: "bottom",
    title: "Simple navigation",
    content: "<p>You can return to the search results without losing the search criteria by clicking on the breadcrumb links.</p>",
  },
  // Step 13: And/Or
  {
    path: "/result/?q=&xkeywords_and_=on&xkeywords=biodiversity&xkeywords=aquaculture&xdate_min=&xdate_max=",
    element: "#facet-xkeywords-container .onoffswitch-label",
    placement: "top",
    title: "Complex filter options",
    content: "<p>You can combine the filters in various ways. For instance, treaties tagged with both <em>Biodiversity</em> and <em>Aquaculture</em>, by using the AND/OR switch when more values are present.</p>",
  },
  // Step 14: Reset
  {
    element: "#facet-xkeywords-container .reset-multiple",
    placement: "top",
    title: "Reset filters",
    content: "<p>Filters can be easily removed using their individual <em>Reset</em> link, or the global <em>Reset all filters</em> button.</p>",
  },
  // Step 15: Remove
  {
    element: ".select2-selection__choice__remove:first",
    placement: "bottom",
    title: "Change filters",
    content: "<p>To remove just one value, use the small red [x] button on the right.</p>",
  },
  // Step 16: Cross-device
  {
    orphan: true,
    title: "Mobile and tablet support",
    content: "<p>You can use ECOLEX on your smartphone or tablet, as well. The layout will automatically adjust to the size of your device.</p><p>Thank you for taking the time and we hope you enjoy using ECOLEX.</p>",
    template: templateNoNav
  }
];

var tour = new Tour({
  name: "tour",
  animation: true,
  keyboard: false,
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

  $('#suggestion a').on('click', function() {
    $('.popover.tour-tour').hide();
  });

  $('[data-toggle="tour"]').on('click', function() {
    tour.restart();
  });

});
