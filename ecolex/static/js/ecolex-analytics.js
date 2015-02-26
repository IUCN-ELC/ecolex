// ecolex ga tracking
// This is used for google analytics on www.ecolex.org
window.addEventListener('load', function () {
  // your code here
  console.log('loading: google-analytics-eaudeweb.');

  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-58379026-1', 'auto');
  ga('send', 'pageview');

  setup_handlers();
}, false);

// Search Type
// ga('set', 'dimension7', dimensionValue);

// Simple Search Hit
// ga('set', 'metric3', metricValue);

// Advanced Search Hit
// ga('set', 'metric4', metricValue);
acc = []; $.each(a, function(i, str) {acc.push(i + "--" + str);})

function count_searches() {
  var params = window.location.search.substring(1).split('&')

  var screen = false;
  var query = false;
  var indexValues = [];

  $.each(params, function(i, str) {
    kv = str.split('=');
    if (kv[0] === "index") {
      indexValues.push(kv[1]);
    }

    if (kv[0] === "query") {
      query = kv[1];
    }

    if (kv[0] === "screen") {
      screen = kv[1];
    }
  };

  // Simple Search
  if (screen === false && query !== false) {
    if (indexValues.length === 0) {
      console.log("SimpleSearch:" + "All");
    } else {
      $.each(indexValues, function(i, str) {
        console.log("SimpleSearch:" + str);
      });
    }

    return;
  }

  if (screen === "Common") {
    if (indexValues.length === 0) {
      console.log("AdvancedSearch:" + "All");
    } else {
      $.each(indexValues, function(i, str) {
        console.log("AdvancedSearch:" + str);
      });
    }
    return;
  }

  if (screen !== false) {
    console.log("AdvancedSearch:" + screen);
    return;
  }

  // Advanced Search
}

function setup_handlers() {
  $(".short_button").click(advanced_list_button_click);

  $("#menu a").click(menu_navigation);

  // search results indexHits restrict links
  $(".indexHits a").click(index_hit_filter_click);

  // search results
  $(".result-date a").click(outbound_link_click);
  $(".input-fields td a").click(record_detail_outbound_link_click);

  $("#searchForm").submit(simple_search_submit);
  $("#advancedSearchForm").submit(advanced_search_submit);
  console.log("handlers set");
}

function simple_search_submit() {
  ga('send', 'event', 'SimpleSearch', 'Submit', 'SimpleSearch');
}

function advanced_search_submit() {
  var title = $("#titleOfText")[0];
  $("input[type=text]").each(function () {
    if (this.value !== "") {
      ga('send', 'event', 'AdvancedSearchOptions', this.name, this.value);
    }
  });

  ga('send', 'event', 'AdvancedSearch', 'Submit', 'AdvancedSearch');
}

function advanced_list_button_click() {
  ga('send', 'event', 'AdvancedSearchOptions', 'List', this.parentElement.children[1].name);
}

function index_hit_filter_click() {
  text = this.innerHTML.split(' ')[0];
  ga('send', 'event', 'AdvancedSearchOptions', 'List', text);
}

function outbound_link_click() {
  var url = this.href;
  var eventAction = "OutboundResultLink";

  if (this.hostname === "faolex.fao.org") {
    eventAction = "FaolexResultLink";
    // Faolex visitor
    ga('set', 'dimension1', true);
    // Faolex visitor session
    ga('set', 'dimension3', true);
    // Faolex hit
    ga('set', 'dimension5', true);
    ga('set', 'metric1', 1);
  } else if (this.hostname === "www.ecolex.org") {
    // Ecolex visitor (internal)
    ga('set', 'dimension2', true);
    // Ecolex visitor session
    ga('set', 'dimension4', true);
    // Ecolex document hit
    ga('set', 'dimension6', true);
    ga('set', 'metric2', 1);
    eventAction = "InternalResultLink";
  }

  ga('send', 'event', 'OutboundLink', eventAction, url);
}

function record_detail_outbound_link_click() {
  var description = this.parentElement.previousElementSibling.innerHTML;

  if (description.match(/Link/g)) {
    outbound_link_click.bind(this)();
  } else {
    ga('send', 'event', "OutboundLink", "OutboundClick", this.href);
  }
}

function menu_navigation() {
  var target = this.innerHTML;
  ga('send', 'event', 'Navigation', target);
}