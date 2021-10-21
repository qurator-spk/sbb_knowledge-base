function LDAvis (data) {

    var that = {};

    // This section sets up the logic for event handling
    var vis_state = {
        lambda: 1,
        topic: 0,
        term: "",
        topic_clicked: 0,
        term_clicked: ""
    };

    // Set up a few 'global' variables to hold the data:
    var K, // number of topics 
    R, // number of terms to display in bar chart
    mdsData, // (x,y) locations and topic proportions
    mdsData3, // topic proportions for all terms in the viz
    lamData, // all terms that are among the top-R most relevant for all topics, lambda values
    lambda = {
        old: 1,
        current: 1
    },
    color1 = "#1f77b4", // baseline color for default topic circles and overall term frequencies
    color2 = "#d62728"; // 'highlight' color for selected topics and term-topic frequencies

    // Set the duration of each half of the transition:
    var duration = 750;

    // Set global margins used for everything (actually, there should be two separate margins for mds/chart
    var margin = {
        top: 0,
        right: 30,
        bottom: 25,
        left: 30
    },
    mdswidth = 530,
    mdsheight = 530,
    barwidth = 365,
    barheight = 530,
    termwidth = 265, // width to add between two panels to display terms
    mdsarea = mdsheight * mdswidth;
    // controls how big the maximum circle can be
    // doesn't depend on data, only on mds width and height:
    var rMax = 60;  

    // proportion of area of MDS plot to which the sum of default topic circle areas is set
    var circle_prop = 0.25;
    var word_prop = 0.25;

    // opacity of topic circles:
    var base_opacity = 0.2,
    highlight_opacity = 0.6;

    // topic/lambda selection names are specific to *this* vis
    var to_select = "#mds"
    var topic_select = to_select + "-topic";
    var lambda_select = to_select + "-lambda";

    // get rid of the # in the to_select (useful) for setting ID values
    var parts = to_select.split("#");
    var visID = parts[parts.length - 1];
    var topicID = visID + "-topic";
    var lambdaID = visID + "-lambda";
    var termID = visID + "-term";
    var termGroupID = visID + "-term-group";
    var wikiID = visID + "-wiki";
    var topicDown = topicID + "-down";
    var topicUp = topicID + "-up";
    var topicClear = topicID + "-clear";

    //////////////////////////////////////////////////////////////////////////////

    // sort array according to a specified object key name 
    // Note that default is decreasing sort, set decreasing = -1 for increasing
    // adpated from http://stackoverflow.com/questions/16648076/sort-array-on-key-value
    function fancysort(key_name, decreasing) {
        decreasing = (typeof decreasing === "undefined") ? 1 : decreasing;
        return function(a, b) {
            if (a[key_name] < b[key_name])
                return 1 * decreasing;
            if (a[key_name] > b[key_name])
                return -1 * decreasing;
            return 0;
        };
    }

    // set the number of topics to global variable K:
    K = data['mdsDat'].x.length;

    // R is the number of top relevant (or salient) words whose bars we display
    R = data['R'];

    // a (K x 5) matrix with columns x, y, topics, Freq, cluster (where x and y are locations for left panel)
    mdsData = [];
    for (var i = 0; i < K; i++) {
        var obj = {};
        for (var key in data['mdsDat']) {
            obj[key] = data['mdsDat'][key][i];
        }
        mdsData.push(obj);
    }

    // a huge matrix with 3 columns: Term, Topic, Freq, where Freq is all non-zero probabilities of topics given terms
    // for the terms that appear in the barcharts for this data
    mdsData3 = [];
    for (var i = 0; i < data['token.table'].Term.length; i++) {
        var obj = {};
        for (var key in data['token.table']) {
            obj[key] = data['token.table'][key][i];
        }
        mdsData3.push(obj);
    }

    // large data for the widths of bars in bar-charts. 6 columns: Term, logprob, loglift, Freq, Total, Category
    // Contains all possible terms for topics in (1, 2, ..., k) and lambda in the user-supplied grid of lambda values
	// which defaults to (0, 0.01, 0.02, ..., 0.99, 1).
    lamData = [];
    for (var i = 0; i < data['tinfo'].Term.length; i++) {
        var obj = {};
        for (var key in data['tinfo']) {
            obj[key] = data['tinfo'][key][i];
        }
        lamData.push(obj);
    }

    // Create the topic input & lambda slider forms. Inspired from:
    // http://bl.ocks.org/d3noob/10632804
    // http://bl.ocks.org/d3noob/10633704
    init_forms(topicID, lambdaID, visID);

    // When the value of lambda changes, update the visualization
    d3.select(lambda_select)
        .on("mouseup", function() {
            // store the previous lambda value
            lambda.old = lambda.current;
            lambda.current = document.getElementById(lambdaID).value;
            vis_state.lambda = +this.value;
            // adjust the text on the range slider
            d3.select(lambda_select).property("value", vis_state.lambda);
            d3.select(lambda_select + "-value").text(vis_state.lambda);
            // transition the order of the bars
            var increased = lambda.old < vis_state.lambda;
            if (vis_state.topic > 0) reorder_bars(increased);
            // store the current lambda value
            that.state_save(true);
            document.getElementById(lambdaID).value = vis_state.lambda;
        });

    d3.select("#" + topicUp).on("click",
        function() {
            // remove term selection if it exists (from a saved URL)
            //that.term_off(vis_state.term);

            var value_old = document.getElementById(topicID).value;
            var value_new = Math.min(K, +value_old + 1).toFixed(0);

            // increment the value in the input box
            document.getElementById(topicID).value = value_new;

            that.topic_off(value_old);

            that.topic_on(value_new);
            that.topic_click(value_new);
            that.state_save(true);
         });

    d3.select("#" + topicDown).on("click",
        function() {
	        // remove term selection if it exists (from a saved URL)
	        //that.term_off(vis_state.term);

            var value_old = document.getElementById(topicID).value;
            var value_new = Math.max(0, +value_old - 1).toFixed(0);

            // increment the value in the input box
            document.getElementById(topicID).value = value_new;
            that.topic_off(value_old);

            that.topic_on(value_new);
            that.topic_click(value_new);
            that.state_save(true);
        });

    d3.select("#" + topicID).on("keyup",
        function() {
            //that.term_off(vis_state.term);

            that.topic_off(vis_state.topic)

            var value_new = document.getElementById(topicID).value;

            if (!isNaN(value_new) && value_new > 0) {
                value_new = Math.min(K, Math.max(1, value_new))

                that.topic_on(value_new);
                vis_state.topic = value_new;
                that.state_save(true);
                document.getElementById(topicID).value = vis_state.topic;

                that.topic_click(value_new);
            }
        });

    d3.select("#" + topicClear)
        .on("click", function() {
            topic_clear();
        });

    // create linear scaling to pixels (and add some padding on outer region of scatterplot)
    var xrange = d3.extent(mdsData, function(d) {
        return d.x;
    });

    //d3.extent returns min and max of an array
    var xdiff = xrange[1] - xrange[0],
    xpad = 0.05;
    var yrange = d3.extent(mdsData, function(d) {
        return d.y;
    });

    var ydiff = yrange[1] - yrange[0],
    ypad = 0.05;

    if (xdiff > ydiff) {
            var xScale = d3.scale.linear()
        .range([0, mdswidth])
        .domain([xrange[0] - xpad * xdiff, xrange[1] + xpad * xdiff]);

            var yScale = d3.scale.linear()
        .range([mdsheight, 0])
        .domain([yrange[0] - 0.5*(xdiff - ydiff) - ypad*xdiff, yrange[1] + 0.5*(xdiff - ydiff) + ypad*xdiff]);
    } else {
            var xScale = d3.scale.linear()
        .range([0, mdswidth])
        .domain([xrange[0] - 0.5*(ydiff - xdiff) - xpad*ydiff, xrange[1] + 0.5*(ydiff - xdiff) + xpad*ydiff]);

            var yScale = d3.scale.linear()
        .range([mdsheight, 0])
        .domain([yrange[0] - ypad * ydiff, yrange[1] + ypad * ydiff]);
    }

    // Create new svg element that contains the MDS plot
    var mds_svg = d3.select("#mds").append("svg")
        .attr("width", "75%")
        .attr("height", "auto")
        .attr("viewBox", `0 0 ${mdswidth + margin.left + margin.right} ${mdsheight + 2 * margin.top + margin.bottom + 2 * rMax}`);

    // Create a group for the mds plot
    var mdsplot = mds_svg.append("g")
        .attr("width", mdswidth + margin.left + margin.right)
        .attr("height", mdsheight + 2 * margin.top + margin.bottom + 2 * rMax)
        .attr("id", "leftpanel")
        .attr("class", "points")
        .attr("transform", "translate(" + margin.left +  "," + 1 * margin.bottom + ")"); //margin.bottom is a hack!!

    // Clicking on the mdsplot should clear the selection
    mdsplot
        .append("rect")
        .attr("x", 0)
        .attr("y", 0)
        .attr("height", mdsheight)
        .attr("width", mdswidth)
        .style("fill", color1)
        .attr("opacity", 0)
        .on("click", function() {
            state_reset();
            that.state_save(true);
        });

    mdsplot.append("line") // draw x-axis
        .attr("x1", 0)
        .attr("x2", mdswidth)
        .attr("y1", mdsheight / 2)
        .attr("y2", mdsheight / 2)
        .attr("stroke", "gray")
        .attr("opacity", 0.3);

    mdsplot.append("text") // label x-axis
        .attr("x", 0)
        .attr("y", mdsheight/2 - 5)
        .text(data['plot.opts'].xlab)
        .attr("fill", "gray");

    mdsplot.append("line") // draw y-axis
        .attr("x1", mdswidth / 2)
        .attr("x2", mdswidth / 2)
        .attr("y1", 0)
        .attr("y2", mdsheight)
        .attr("stroke", "gray")
        .attr("opacity", 0.3);

    mdsplot.append("text") // label y-axis
        .attr("x", mdswidth/2 + 5)
        .attr("y", 7)
        .text(data['plot.opts'].ylab)
        .attr("fill", "gray");

    // new definitions based on fixing the sum of the areas of the default topic circles:
    var newSmall = Math.sqrt(0.02*mdsarea*circle_prop/Math.PI);
    var newMedium = Math.sqrt(0.05*mdsarea*circle_prop/Math.PI);
    var newLarge = Math.sqrt(0.10*mdsarea*circle_prop/Math.PI);
    var cx = 10 + newLarge;
    var cx2 = cx + 1.5 * newLarge;
	
    // circle guide inspired from
    // http://www.nytimes.com/interactive/2012/02/13/us/politics/2013-budget-proposal-graphic.html?_r=0
    circleGuide =
        function(rSize, size) {
            d3.select("#leftpanel").append("circle")
                .attr('class', "circleGuide" + size)
                .attr('r', rSize)
                .attr('cx', cx)
                .attr('cy', mdsheight + rSize)
                .style('fill', 'none')
                .style('stroke-dasharray', '2 2')
                .style('stroke', '#999');
            d3.select("#leftpanel").append("line")
                .attr('class', "lineGuide" + size)
                .attr("x1", cx)
                .attr("x2", cx2)
                .attr("y1", mdsheight + 2 * rSize)
                .attr("y2", mdsheight + 2 * rSize)
                .style("stroke", "gray")
                .style("opacity", 0.3);
        };

    circleGuide(newSmall, "Small");
    circleGuide(newMedium, "Medium");
    circleGuide(newLarge, "Large");

    var defaultLabelSmall = "2%";
    var defaultLabelMedium = "5%";
    var defaultLabelLarge = "10%";

    d3.select("#leftpanel").append("text")
        .attr("x", 10)
        .attr("y", mdsheight - 10)
        .attr('class', "circleGuideTitle")
        .style("text-anchor", "left")
        .style("fontWeight", "bold")
        .text("Marginal topic distribution");

    d3.select("#leftpanel").append("text")
        .attr("x", cx2 + 10)
        .attr("y", mdsheight + 2 * newSmall)
        .attr('class', "circleGuideLabelSmall")
        .style("text-anchor", "start")
        .text(defaultLabelSmall);

    d3.select("#leftpanel").append("text")
        .attr("x", cx2 + 10)
        .attr("y", mdsheight + 2 * newMedium)
        .attr('class', "circleGuideLabelMedium")
        .style("text-anchor", "start")
        .text(defaultLabelMedium);

    d3.select("#leftpanel").append("text")
        .attr("x", cx2 + 10)
        .attr("y", mdsheight + 2 * newLarge)
        .attr('class', "circleGuideLabelLarge")
        .style("text-anchor", "start")
        .text(defaultLabelLarge);

    // bind mdsData to the points in the left panel:
    var points = mdsplot.selectAll("points")
        .data(mdsData)
        .enter();

    // text to indicate topic
    points.append("text")
        .attr("class", "txt")
        .attr("x", function(d) {
            return (xScale(+d.x));
        })
        .attr("y", function(d) {
            return (yScale(+d.y) + 4);
        })
        .attr("stroke", "black")
        .attr("opacity", 1)
        .style("text-anchor", "middle")
        .style("font-size", "11px")
        .style("fontWeight", 100)
        .text(function(d) {
            return d.topics;
        });

    // draw circles
    points.append("circle")
        .attr("class", "dot")
        .style("opacity", 0.2)
        .style("fill", color1)
        .attr("r", function(d) {
            //return (rScaleMargin(+d.Freq));
            return (Math.sqrt((d.Freq/100)*mdswidth*mdsheight*circle_prop/Math.PI));
        })
        .attr("cx", function(d) {
            return (xScale(+d.x));
        })
        .attr("cy", function(d) {
            return (yScale(+d.y));
        })
        .attr("stroke", "black")
        .attr("id", function(d) {
            return (topicID + d.topics)
        })
        .on("mouseover",
        function(d) {
            var old_topic = topicID + vis_state.topic;
            if ((vis_state.topic > 0) && (old_topic != this.id)) {
                that.topic_off(vis_state.topic);
            }
            that.topic_on(d.topics);
        })
        .on("click",
        function(d) {
            // prevent click event defined on the div container from firing
            // http://bl.ocks.org/jasondavies/3186840
            d3.event.stopPropagation();

            var old_topic = topicID + vis_state.topic;
            if ((vis_state.topic > 0) && (old_topic != this.id)) {
                that.topic_off(vis_state.topic);
            }
            // make sure topic input box value and fragment reflects clicked selection
            document.getElementById(topicID).value = d.topics;

            that.topic_on(d.topics);
            that.topic_click(d.topics);

            that.state_save(true);
        })
        .on("mouseout", function(d) {
            if (vis_state.topic != d.topics) that.topic_off(d.topics);

            if (vis_state.topic > 0) that.topic_on(vis_state.topic);
        });

    d3.select("#mds-heading").text("Intertopic Distance Map (via multidimensional scaling)")

    // establish layout and vars for bar chart
    var barDefault2 = lamData.filter(function(d) {
        return d.Category == "Default"
    });

    var y = d3.scale.ordinal()
        .domain(barDefault2.map(function(d) {
            return d.Term;
        }))
        .rangeRoundBands([0, barheight], 0.15);
    var x = d3.scale.linear()
        .domain([0, d3.max(barDefault2, function(d) {
            return d.Total;
        })])
        .range([0, barwidth])
        .nice();
    var yAxis = d3.svg.axis()
        .scale(y);

    // Create new svg element that contains the bar chart.
    var chart_svg = d3.select("#chart").append("svg")
        //.attr("width", barwidth + termwidth  + margin.left + margin.right)
        //.attr("height", barheight + 2 * margin.bottom + 5);
        .attr("width", "75%")
        .attr("height", "auto")
        .attr("viewBox", `0 0 ${barwidth + termwidth  + margin.left + margin.right} ${barheight + 2 * margin.bottom + 5}`);

    var chart = chart_svg.append("g")
        .attr("width", barwidth + termwidth  + margin.left + margin.right)
        .attr("height", barheight + 2 * margin.bottom + 5)
        .attr("transform", "translate(" + +(termwidth + margin.left) + ", " + "13)")
        .attr("id", "bar-freqs");

    // bar chart legend/guide:
    var barguide = {"width": 100, "height": 15};

    d3.select("#bar-freqs").append("rect")
        .attr("x", 0)
        .attr("y", mdsheight + 10)
        .attr("height", barguide.height)
        .attr("width", barguide.width)
        .style("fill", color1)
        .attr("opacity", 0.4);

    d3.select("#bar-freqs").append("text")
        .attr("x", barguide.width + 5)
        .attr("y", mdsheight + 10 + barguide.height/2)
        .style("dominant-baseline", "middle")
        .text("Overall term frequency");

    d3.select("#bar-freqs").append("rect")
        .attr("x", 0)
        .attr("y", mdsheight + 10 + barguide.height + 5)
        .attr("height", barguide.height)
        .attr("width", barguide.width/2)
        .style("fill", color2)
        .attr("opacity", 0.8);

    d3.select("#bar-freqs").append("text")
        .attr("x", barguide.width/2 + 5)
        .attr("y", mdsheight + 10 + (3/2)*barguide.height + 5)
        .style("dominant-baseline", "middle")
        .text("Estimated term frequency within the selected topic");

    // Bind 'default' data to 'default' bar chart
    var basebars = chart.selectAll(".bar-totals")
        .data(barDefault2)
        .enter();

    // Draw the gray background bars defining the overall frequency of each word
    basebars
        .append("rect")
        .attr("class", "bar-totals")
        .attr("x", 0)
        .attr("y", function(d) {
            return y(d.Term);
        })
        .attr("height", y.rangeBand())
        .attr("width", function(d) {
            return x(d.Total);
        })
        .style("fill", color1)
        .attr("opacity", 0.4);

    // Add word labels to the side of each bar
    var labels = basebars
            .append("g")
            //.attr("x", -5)
            //.attr("y", function(d) {
            //    return y(d.Term) + 12 + barheight + margin.bottom + 2 * rMax;
            //})
            .attr("transform", function(d) {
                return "translate(-25, " + (y(d.Term) + 12) + ")";
            })
            .attr("class", "term-group")
            .attr("id", function(d) {
                return (termGroupID + d.Term)
            });

    labels.append("text")
        .attr("class", "terms")
        .attr("cursor", "pointer")
        .attr("id", function(d) {
                return (termID + d.Term)
            })
        .style("text-anchor", "end") // right align text - use 'middle' for center alignment
        .text(function(d) {
            return d.Term;
        })
        .on("mouseover", function() {
            that.term_hover(this.innerHTML);
        })
        .on("mouseout", function() {
            that.term_off(this.__data__.Term);
        })
        .on("click", function() {
                that.term_click(this.__data__.Term);
                that.state_save(true);
            }
        );

    labels
        .append("a")
        .attr("class", "wikidata")
        .attr("id", function(d) {
            return (wikiID + d.Term)
        })
        .attr("xlink:href",
            function(d) {

                var qidMatcher = /^(Q[0-9]+)\(/g;

                var result = qidMatcher.exec(d.Term);

                return "https://wikidata.org/wiki/" + result[1];
            })
        .append("text")
        .html("&nbsp;[&#8594;]");

	d3.select("#chart-heading").html("Most Salient Terms<sup>(1)</sup>")
	
    // barchart axis adapted from http://bl.ocks.org/mbostock/1166403
    var xAxis = d3.svg.axis().scale(x)
        .orient("top")
        .tickSize(-barheight)
        .tickSubdivide(true)
        .ticks(6);

    chart.attr("class", "xaxis")
        .call(xAxis);

	// dynamically create the topic and lambda input forms at the top of the page:
    function init_forms(topicID, lambdaID, visID) {

        // Create the svg to contain the slider scale:
        var scaleContainer =
            d3.select("#sliderdiv").append("svg")
            .attr("width", 250)
            .attr("height", 25);

        var sliderScale =
            d3.scale.linear()
            .domain([0, 1])
            .range([7.5, 242.5])  // trimmed by 7.5px on each side to match the input type=range slider:
            .nice();

        // adapted from http://bl.ocks.org/mbostock/1166403
        var sliderAxis =
            d3.svg.axis()
            .scale(sliderScale)
            .orient("bottom")
            .tickSize(10)
            .tickSubdivide(true)
            .ticks(6);

        // group to contain the elements of the slider axis:
        var sliderAxisGroup =
            scaleContainer.append("g")
            .attr("class", "slideraxis")
            .attr("margin-top", "-10px")
            .call(sliderAxis);
    }

    // function to re-order the bars (gray and red), and terms:
    function reorder_bars(increase) {

        var term_clicked_id = termID + vis_state.term_clicked;

        if (vis_state.term_clicked != "") {
            var termClickedElem = document.getElementById(term_clicked_id);

            if (termClickedElem != null) {
                termClickedElem.style.textDecoration = null;
                //console.log("reorder_bars: 651(textDecoration=null): " + termClickedElem.id);
            }
        }

        var termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "normal";
            //console.log("reorder_bars: 659(normal)" + termElem.id);
        }

        // grab the bar-chart data for this topic only:
        var dat2 = lamData.filter(
            function(d) {
            //return d.Category == "Topic" + Math.min(K, Math.max(0, vis_state.topic)) // fails for negative topic numbers...
                return d.Category == "Topic" + vis_state.topic;
            });

        // define relevance:
        for (var i = 0; i < dat2.length; i++) {
            dat2[i].relevance =
                vis_state.lambda * dat2[i].logprob + (1 - vis_state.lambda) * dat2[i].loglift;
        }

        // sort by relevance:
        dat2.sort(fancysort("relevance"));

        // truncate to the top R tokens:
        var dat3 = dat2.slice(0, R);

        var y = d3.scale.ordinal()
            .domain(dat3.map(function(d) {
                return d.Term;
            }))
            .rangeRoundBands([0, barheight], 0.15);

        var x = d3.scale.linear()
            .domain([0, d3.max(dat3, function(d) {
                return d.Total;
            })])
            .range([0, barwidth])
            .nice();

        // Change Total Frequency bars
        var graybars = d3.select("#bar-freqs")
            .selectAll(".bar-totals")
            .data(dat3, function(d) { return d.Term; });

        var labels = d3.select("#bar-freqs")
            .selectAll(".term-group")
            .data(dat3, function(d) { return d.Term; });

        // Create red bars (drawn over the gray ones) to signify the frequency under the selected topic
        var redbars = d3.select("#bar-freqs")
            .selectAll(".overlay")
            .data(dat3, function(d) {
                return d.Term;
            });

        // adapted from http://bl.ocks.org/mbostock/1166403
        var xAxis = d3.svg.axis().scale(x)
            .orient("top")
            .tickSize(-barheight)
            .tickSubdivide(true)
            .ticks(6);

        // New axis definition:
        var newaxis = d3.selectAll(".xaxis");

        // define the new elements to enter:
        var graybarsEnter = graybars.enter()
            .append("rect")
            .attr("class", "bar-totals")
            .attr("x", 0)
            .attr("y", function(d) {
                return y(d.Term) + barheight + margin.bottom + 2 * rMax;
            })
            .attr("height", y.rangeBand())
            .style("fill", color1)
            .attr("opacity", 0.4);

        var labelsEnter = labels.enter()
            .append("g")
            .attr("x", -5)
            .attr("transform", function(d) {
                return "translate(-25, " + (y(d.Term) + 12 + barheight + margin.bottom + 2 * rMax) + ")";
            })
            .attr("class", "term-group")
            .attr("id", function(d) {
                return (termGroupID + d.Term)
            });

        labelsEnter.append("text")
            .attr("class", "terms")
            .attr("cursor", "pointer")
            .attr("id", function(d) {
                return (termID + d.Term)
            })
            .style("text-anchor", "end")
            .text(function(d) { return d.Term; })
            .on("mouseover", function() {
                that.term_hover(this.innerHTML);
            })
            .on("mouseout", function() {
                that.term_off(this.__data__.Term);
            })
            .on("click", function() {
                that.term_click(this.__data__.Term);
                that.state_save(true);
            });

        labelsEnter
            .append("a")
            .attr("class","wikidata")
            .attr("id", function(d) {
                return (wikiID + d.Term)
            })
            .attr("xlink:href",
                function(d) {

                    var qidMatcher = /^(Q[0-9]+)\(/g;

                    var matches = qidMatcher.exec(d.Term);

                    return "https://wikidata.org/wiki/" + matches[1];
                })
            .append("text")
            .html("&nbsp;[&#8594;]");

        var redbarsEnter = redbars.enter().append("rect")
            .attr("class", "overlay")
            .attr("x", 0)
            .attr("y", function(d) {
                return y(d.Term) + barheight + margin.bottom + 2 * rMax;
            })
            .attr("height", y.rangeBand())
            .style("fill", color2)
            .attr("opacity", 0.8);

        if (increase) {
            graybarsEnter
                .attr("width", function(d) {
                    return x(d.Total);
                })
                .transition().duration(duration)
                .delay(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                });

            labelsEnter
                .transition().duration(duration)
                .delay(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (y(d.Term) + 12) + ")";
                });

            redbarsEnter
                .attr("width", function(d) {
                    return x(d.Freq);
                })
                .transition().duration(duration)
                .delay(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                });

            graybars.transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Total);
                })
                .transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                });

            labels.transition().duration(duration)
                .delay(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (y(d.Term) + 12) + ")";
                });

            redbars.transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Freq);
                })
                .transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                });

            // Transition exiting rectangles to the bottom of the barchart:
            graybars.exit()
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Total);
                })
                .transition().duration(duration)
                .attr("y", function(d, i) {
                    return barheight + margin.bottom + 6 + i * 18;
                })
                .remove();

            labels.exit()
                .transition().duration(duration)
                .delay(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (barheight + margin.bottom + 18 + i * 18) + ")";
                })
                .remove();

            redbars.exit()
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Freq);
                })
                .transition().duration(duration)
                .attr("y", function(d, i) {
                    return barheight + margin.bottom + 6 + i * 18;
                })
                .remove();

            // https://github.com/mbostock/d3/wiki/Transitions#wiki-d3_ease
            newaxis.transition().duration(duration)
                .call(xAxis)
                .transition().duration(duration);

        } else {
            graybarsEnter
                .attr("width", 100) // FIXME by looking up old width of these bars
                .transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                })
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Total);
                });

            labelsEnter
                .transition().duration(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (y(d.Term) + 12) + ")";
                });


            redbarsEnter
                .attr("width", 50) // FIXME by looking up old width of these bars
                .transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                })
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Freq);
                });

            graybars.transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                })
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Total);
                });

            labels.transition().duration(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (y(d.Term) + 12) + ")";
                });

            redbars.transition().duration(duration)
                .attr("y", function(d) {
                    return y(d.Term);
                })
                .transition().duration(duration)
                .attr("width", function(d) {
                    return x(d.Freq);
                });

            // Transition exiting rectangles to the bottom of the barchart:
            graybars.exit()
                .transition().duration(duration)
                .attr("y", function(d, i) {
                    return barheight + margin.bottom + 6 + i * 18 + 2 * rMax;
                })
                .remove();

            labels.exit()
                .transition()
                .duration(duration)
                .attr("transform", function(d) {
                    return "translate(-25," + (barheight + margin.bottom + 18 + i * 18 + 2 * rMax) + ")";
                })
                .remove();

            redbars.exit()
                .transition().duration(duration)
                .attr("y", function(d, i) {
                    return barheight + margin.bottom + 6 + i * 18 + 2 * rMax;
                })
                .remove();

            // https://github.com/mbostock/d3/wiki/Transitions#wiki-d3_ease
            newaxis.transition().duration(duration)
                .transition().duration(duration)
                .call(xAxis);
        }

        term_clicked_id = termID + vis_state.term_clicked;

        if (vis_state.term_clicked != "") {
            var termClickedElem = document.getElementById(term_clicked_id);

            if (termClickedElem != null) {
                termClickedElem.style.textDecoration = "underline";
                //console.log("topic_on: 954(underline): " + termClickedElem.id);
            }
        }

        termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "bold";
            //console.log("topic_on: 962(bold)" + termElem.id);
        }
    }

    //////////////////////////////////////////////////////////////////////////////

    // function to update bar chart when a topic is selected
    // the circle argument should be the appropriate circle element
    that.topic_on = function(topic) {

        if (topic < 1) return;

        var circle = document.getElementById(topicID + topic);

        if ((circle !== null) && (circle !== undefined)) {

            // grab data bound to this element
            var d = circle.__data__
            var Freq = Math.round(d.Freq * 10) / 10,
            topics = d.topics;

            // change opacity and fill of the selected circle
            circle.style.opacity = highlight_opacity;
            circle.style.fill = color2;
        }

        var termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "normal";
            //console.log("topic_on: 992(normal):" + termElem.id);
        }

        // set text with info relevant to topic of interest
        d3.select("#chart-heading").text("Top-" + R + " Most Relevant Terms for Topic " + topics + " (" + Freq + "% of tokens)");
        $("#lambdaInput").removeClass("d-none");
        $("#doc-card").removeClass("d-none");

        // grab the bar-chart data for this topic only:
        var dat2 = lamData.filter(
            function(d) {
                return d.Category == "Topic" + topics
            });

        // define relevance:
        for (var i = 0; i < dat2.length; i++) {
            dat2[i].relevance = lambda.current * dat2[i].logprob +
                (1 - lambda.current) * dat2[i].loglift;
        }

        // sort by relevance:
        dat2.sort(fancysort("relevance"));

        // truncate to the top R tokens:
        var dat3 = dat2.slice(0, R);

        // scale the bars to the top R terms:
        var y = d3.scale.ordinal()
            .domain(dat3.map(function(d) {
                return d.Term;
            }))
            .rangeRoundBands([0, barheight], 0.15);

        var x = d3.scale.linear()
            .domain([0, d3.max(dat3, function(d) {
                return d.Total;
            })])
            .range([0, barwidth])
            .nice();

        // remove the red bars if there are any:
        d3.selectAll(".overlay").remove();

        // Change Total Frequency bars
        d3.selectAll(".bar-totals")
            .data(dat3)
            .attr("x", 0)
            .attr("y", function(d) {
                return y(d.Term);
            })
            .attr("height", y.rangeBand())
            .attr("width", function(d) {
                return x(d.Total);
            })
            .style("fill", color1)
            .attr("opacity", 0.4);

        // Change wikidata links
        d3.selectAll(".wikidata")
            .data(dat3)
            .attr("id", function(d) {
                return (wikiID + d.Term)
            })
            .attr("xlink:href",
            function(d) {

                var qidMatcher = /^(Q[0-9]+)\(/g;

                var result = qidMatcher.exec(d.Term);

                return "https://wikidata.org/wiki/" + result[1];
            });

        // Change word labels
        d3.selectAll(".term-group")
            .data(dat3)
            .attr("id", function(d) {
                return (termGroupID + d.Term)
            })
            .attr("transform", function(d) {
                return "translate(-25," + (y(d.Term) + 12) + ")";
            });

        d3.selectAll(".terms")
            .data(dat3)
            .attr("id", function(d) {
                return (termID + d.Term)
            })
            .style("text-anchor", "end") // right align text - use 'middle' for center alignment
            .text(function(d) {
                return d.Term;
            });


        // Create red bars (drawn over the gray ones) to signify the frequency under the selected topic
        d3.select("#bar-freqs").selectAll(".overlay")
            .data(dat3)
            .enter()
            .append("rect")
            .attr("class", "overlay")
            .attr("x", 0)
            .attr("y", function(d) {
                return y(d.Term);
            })
            .attr("height", y.rangeBand())
            .attr("width", function(d) {
                return x(d.Freq);
            })
            .style("fill", color2)
            .attr("opacity", 0.8);

        // adapted from http://bl.ocks.org/mbostock/1166403
        var xAxis = d3.svg.axis().scale(x)
            .orient("top")
            .tickSize(-barheight)
            .tickSubdivide(true)
            .ticks(6);

        // redraw x-axis
        d3.selectAll(".xaxis")
        //.attr("class", "xaxis")
            .call(xAxis);

        var term_clicked_id = termID + vis_state.term_clicked;

        if (vis_state.term_clicked != "") {
            var termClickedElem = document.getElementById(term_clicked_id);

            if (termClickedElem != null) {
                termClickedElem.style.textDecoration = "underline";
                //console.log("topic_on: 1105(underline): " + termClickedElem.id);
            }
        }

        termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "bold";
            //console.log("topic_on: 1113(bold)" + termElem.id);
        }
    }

    that.topic_off = function (topic) {

        var circle = document.getElementById(topicID + topic);

        if ((circle !== null) && (circle !== undefined)) {
        // go back to original opacity/fill
            circle.style.opacity = base_opacity;
            circle.style.fill = color1;
        }

        // whenever the topic changes we have to remove the underline style
        // from any clicked term
        var old_term_clicked_id = termID + vis_state.term_clicked;
        var topic_clicked_id = topicID + vis_state.topic_clicked;
        if  (vis_state.term_clicked != "") {
            var oldtermElem = document.getElementById(old_term_clicked_id);
            if (oldtermElem != null) {
                oldtermElem.style.textDecoration = null;
                //console.log("topic_off: 1135(oldtermElem.style.textDecoration = null): " + oldtermElem.id);
            }
        }

        var termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "normal";
            //console.log("topic_off: 1141(normal): " + termElem.id);
        }

        d3.select("#chart-heading").html("Top-" + R + " Most Salient Terms <sup>(1)</sup>");
        $("#lambdaInput").addClass("d-none");
        $("#doc-card").addClass("d-none");

        // remove the red bars
        d3.selectAll(".overlay").remove();

        // go back to 'default' bar chart
        var dat2 = lamData.filter(function(d) {
            return d.Category == "Default"
        });

        var y = d3.scale.ordinal()
            .domain(dat2.map(function(d) {
                return d.Term;
            }))
            .rangeRoundBands([0, barheight], 0.15);
        var x = d3.scale.linear()
            .domain([0, d3.max(dat2, function(d) {
                return d.Total;
            })])
            .range([0, barwidth])
            .nice();

        // Change Total Frequency bars
        d3.selectAll(".bar-totals")
            .data(dat2)
            .attr("x", 0)
            .attr("y", function(d) {
                return y(d.Term);
            })
            .attr("height", y.rangeBand())
            .attr("width", function(d) {
                return x(d.Total);
            })
            .style("fill", color1)
            .attr("opacity", 0.4);

        // Change wikidata links
        d3.selectAll(".wikidata")
            .data(dat2)
            .attr("xlink:href",
            function(d) {

                var qidMatcher = /^(Q[0-9]+)\(/g;

                var result = qidMatcher.exec(d.Term);

                return "https://wikidata.org/wiki/" + result[1];
            })
            .exit().remove();

        //Change word labels
        d3.selectAll(".term-group")
            .data(dat2)
            //.attr("x", -5)
            .attr("id", function(d) {
                return termGroupID + d.Term;
            })
            .attr("transform", function(d) {
                return "translate(-25," + (y(d.Term) + 12) + ")";
            }).exit().remove();

        d3.selectAll(".terms")
            .data(dat2)
            .style("text-anchor", "end") // right align text - use 'middle' for center alignment
            .attr("id", function(d) {
                return termID + d.Term;
            })
            .text(function(d) {
                return d.Term;
            });

        // adapted from http://bl.ocks.org/mbostock/1166403
        var xAxis = d3.svg.axis().scale(x)
            .orient("top")
            .tickSize(-barheight)
            .tickSubdivide(true)
            .ticks(6);

        // redraw x-axis
        d3.selectAll(".xaxis")
            .attr("class", "xaxis")
            .call(xAxis);

        termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "bold";
            //console.log("topic_off: 1233(bold): " + termElem.id);
        }
    }

    // event definition for mousing over a term
    that.term_hover = function(term) {

        if (vis_state.term != term) {
            that.term_off(vis_state.term);
            that.term_on(term);
        }
    }

    // updates vis when a term is selected via click or hover
    that.term_on = function (term) {

        if (term == null) return null;

        var dat2 = mdsData3.filter(function(d2) {
            return d2.Term == term
        });

        var k = dat2.length; // number of topics for this token with non-zero frequency

        var radius = [];
        for (var i = 0; i < K; ++i) {
            radius[i] = 0;
        }
        for (i = 0; i < k; i++) {
            radius[dat2[i].Topic - 1] = dat2[i].Freq;
        }

        var size = [];
        for (var i = 0; i < K; ++i) {
            size[i] = 0;
        }
        for (i = 0; i < k; i++) {
            // If we want to also re-size the topic number labels, do it here
            // 11 is the default, so leaving this as 11 won't change anything.
            size[dat2[i].Topic - 1] = 11;
        }

        var rScaleCond = d3.scale.sqrt()
            .domain([0, 1]).range([0, rMax]);

        // Change size of bubbles according to the word's distribution over topics
        d3.selectAll(".dot")
            .data(radius)
            .transition()
            .attr("r", function(d) {
                //return (rScaleCond(d));
	    return (Math.sqrt(d*mdswidth*mdsheight*word_prop/Math.PI));
            });

        // re-bind mdsData so we can handle multiple selection
        d3.selectAll(".dot")
            .data(mdsData)

        // Change sizes of topic numbers:
        d3.selectAll(".txt")
            .data(size)
            .transition()
            .style("font-size", function(d) {
                return +d;
            });

        // Alter the guide
        d3.select(".circleGuideTitle")
            .text("Conditional topic distribution given term = '" + term + "'");


        var termElem = null;

        if (vis_state.term !== "") {
            termElem = document.getElementById(termID + vis_state.term);

            if ((termElem !== undefined) && (termElem !== null)) {
                termElem.style["fontWeight"] = "normal";
                //console.log("term_on: 1315(normal): " + termElem.id);
            }
        }

        vis_state.term = term;

        termElem = document.getElementById(termID + term);

        if ((termElem !== undefined) && (termElem !== null)) {
            termElem.style["fontWeight"] = "bold";
            //console.log("term_on: 1325(bold): " + termElem.id)
        }
    }

    that.term_off = function (term) {

        d3.selectAll(".dot")
            .data(mdsData)
            .transition()
            .attr("r", function(d) {
                //return (rScaleMargin(+d.Freq));
                return (Math.sqrt((d.Freq/100)*mdswidth*mdsheight*circle_prop/Math.PI));
            });

        // Change sizes of topic numbers:
        d3.selectAll(".txt")
            .transition()
            .style("font-size", "11px");

        // Go back to the default guide
        d3.select(".circleGuideTitle")
            .text("Marginal topic distribution");
        d3.select(".circleGuideLabelLarge")
            .text(defaultLabelLarge);
        d3.select(".circleGuideLabelSmall")
            .attr("y", mdsheight + 2 * newSmall)
            .text(defaultLabelSmall);
        d3.select(".circleGuideSmall")
            .attr("r", newSmall)
            .attr("cy", mdsheight + newSmall);
        d3.select(".lineGuideSmall")
            .attr("y1", mdsheight + 2 * newSmall)
            .attr("y2", mdsheight + 2 * newSmall);

        var termElem = null;

        if (term !== "") termElem = document.getElementById(termID + term);
        else termElem = document.getElementById(termID + vis_state.term);

        if ((termElem !== undefined) && (termElem !== null)) {
                termElem.style["fontWeight"] = "normal";
                //console.log("term_off: 1368(normal):" + termElem.id);
        }

        vis_state.term = "";
    }


    that.state_url = function () {

        var term_param="";
        if (vis_state.term_clicked !== "") {
            term_param = "&term=" + vis_state.term_clicked;
        }

        return location.origin + location.pathname + "?topic=" + vis_state.topic +
            "&lambda=" + vis_state.lambda + term_param;
    }

    that.state_save = function(replace) {
        if (replace)
            history.replaceState(vis_state, "Query", that.state_url());
        else
            history.pushState(vis_state, "Query", that.state_url());
    }

    function topic_clear() {
        if (vis_state.topic > 0) {
            that.topic_off(vis_state.topic);

            // set the style of any topic clicked to be back to regular style
            // (no thick border around topic circle)
            var old_topic_clicked_id = topicID + vis_state.topic_clicked;
            if (vis_state.topic_clicked > 0) {
                document.getElementById(old_topic_clicked_id).style.strokeWidth = null;
            }
        }

        // set state of topic_clicked to 0, so we can click on topic x, reset
        // vis, then click on topic x again without any problems
        vis_state.topic_clicked = 0;

        document.getElementById(topicID).value = vis_state.topic = 0;

        that.state_save(true);
    }

    function state_reset() {

        // set the style of any clicked term back to be non-underline
        var old_term_clicked_id = termID + vis_state.term_clicked;
        if (vis_state.term_clicked != "") {
            var oldterm = document.getElementById(old_term_clicked_id);
            if (oldterm != null) {
                oldterm.style.textDecoration = null;
            }
        }

        that.term_off(vis_state.term);

        topic_clear();

        // make sure term ids are all correct
        d3.selectAll(".term-group").attr("id", function(d) {
            return (termGroupID + d.Term)
        });

        d3.selectAll(".term").attr("id", function(d) {
            return (termID + d.Term)
        });

        // make sure wikidata ids are all correct
        d3.selectAll(".wikidata").attr("id", function(d) {
            return (wikiID + d.Term)
        });
    }

    that.topic_click =
        function (newtopic_num) {

            var new_topic_clicked_id = topicID + newtopic_num;

            // set style of clicked topic to have thicker border
            var topicElem = document.getElementById(new_topic_clicked_id);

            if ((topicElem !== undefined) && (topicElem !== null)){
                topicElem.style.strokeWidth = 2;
            }

            // set style of old selected topic back to regular border
            var old_topic_clicked_id = topicID + vis_state.topic_clicked;
            if (vis_state.topic_clicked > 0 && old_topic_clicked_id != new_topic_clicked_id) {
                document.getElementById(old_topic_clicked_id).style.strokeWidth = null;
            }

            ////console.log(newtopic_num);

            // save state of topic clicked
            vis_state.topic = newtopic_num;
            vis_state.topic_clicked = newtopic_num;
        };

    that.term_click = function(term) {

        var termElem = null;

        if (term !== "") {
            termElem = document.getElementById(termID + term);
        }

        if ((termElem !== undefined) && (termElem !== null)) {
            // underline clicked term
            termElem.style.textDecoration = "underline";
            //console.log("term_click: 1481(underline): " + termElem.id)
        }

        // set style of old clicked term back to non-underline
        var old_term_clicked_id = termID + vis_state.term_clicked;

        if (old_term_clicked_id != termID + term) {
            var oldtermElem = document.getElementById(old_term_clicked_id);

            if ((oldtermElem !== null) && (oldtermElem !== undefined)) {
                oldtermElem.style.textDecoration = null;
            }
        }

        // save state of term clicked
        vis_state.term_clicked = term;
        //console.log("term_click 1497 vis_state.term_clicked = " + term);
    }


    function init_state() {

        // Idea: write a function to parse the URL string
        // only accept values in [0,1] for lambda, {0, 1, ..., K} for topics (any string is OK for term)
        // Allow for subsets of the three to be entered:
        // (1) topic only (lambda = 1 term = "")
        // (2) lambda only (topic = 0 term = "") visually the same but upon hovering a topic, the effect of lambda will be seen
        // (3) term only (topic = 0 lambda = 1) only fires when the term is among the R most salient
        // (4) topic + lambda (term = "")
        // (5) topic + term (lambda = 1)
        // (6) lambda + term (topic = 0) visually lambda doesn't make a difference unless a topic is hovered
        // (7) topic + lambda + term

        // Short-term: assume format of "#topic=k&lambda=l&term=s" where k, l, and s are strings (b/c they're from a URL)

        // serialize the visualization state using fragment identifiers -- http://en.wikipedia.org/wiki/Fragment_identifier
        // location.hash holds the address information

        var url_params = new URLSearchParams(window.location.search);

        if (url_params.has("lambda")) {
            vis_state.lambda=Number(url_params.get("lambda"));

            // Force l (lambda identifier) to be in [0, 1]:
            vis_state.lambda = Math.min(1, Math.max(0, vis_state.lambda));

            // impose the value of lambda:
            document.getElementById(lambdaID).value = vis_state.lambda;
            document.getElementById(lambdaID + "-value").innerHTML = vis_state.lambda;

            lambda.current = vis_state.lambda;
        }

        if (url_params.has("topic")) {
            vis_state.topic=Number(url_params.get("topic"));

            // Force k (topic identifier) to be an integer between 0 and K:
            vis_state.topic = Math.round(Math.min(K, Math.max(0, vis_state.topic)));

            // select the topic and transition the order of the bars (if approporiate)
            if (!isNaN(vis_state.topic)) {
                document.getElementById(topicID).value = vis_state.topic;

                if (vis_state.topic > 0) that.topic_on(vis_state.topic);

                if (vis_state.lambda < 1 && vis_state.topic > 0) {
                    reorder_bars(false);
                }
            }

            if (vis_state.topic == 0) {
                $("#lambdaInput").addClass("d-none");
                $("#doc-card").addClass("d-none");
            }
        }

        if (url_params.has("term")) {
            that.term_click(url_params.get("term"));
        }
    };

    init_state();

    return that;
}

