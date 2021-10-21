
function NED(ner_url, parse_url, ned_url,
            result_text_element="#result-text", result_entities_element="#result-entities",
            ner_result=null, ned_result={}) {

    var that = null;
    var ner_parsed = null;

    var spinner_html =
            `<div class="d-flex justify-content-center mt-5">
                <div class="spinner-border align-center mt-5" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
             </div>`;

    var el_html =
         `<div class="card">
            <div class="card-header">
                <p> <b> Entity-Linking: </b> </p>
                <span class="ml-1" style="padding: 2px;border-style:dotted;border-width: thin;border-radius: 20px;border-color: gray">EL not availabe </span>
                <span class="ml-1" style="padding: 2px;border-style:solid;border-width: thin;border-radius: 20px;border-color: gray">EL-conf-low </span>
                <span class="ml-1" style="padding: 2px;border-style:solid;border-width: 2px;border-radius: 20px;border-color: gray">EL-conf-medium </span>
            </div>
            <div class="card-body" id="linking-list">
            </div>
        </div>`;

    var el_search_html =
        `
        <div class="card">
            <div class="card-header">
                <p class"my-auto"> <b> Search-for-QID: </b></p>
            </div>
            <div class="card-body">
                <div class="input-group justify-content-center">
                  <div class="input-group-prepend">
                    <button class="btn btn-outline-secondary" type="button" id="entity-prev">Prev</button>
                  </div>
                  <input type="text" list="suggestions" id="search-for" autocomplete="off">
                  <datalist id="suggestions"></datalist>
                  </input>
                  <div class="input-group-append">
                    <button class="btn btn-outline-secondary" type="button" id="entity-next">Next</button>
                  </div>
                </div>
            </div>
        </div>
        `;

    var text_region_html =
        `<div class="card">
            <div class="card-header" id="doc-title">
                <b>Ergebnis:</b>
            </div>
            <div class="card-block">
                <div id="ner-text" style="overflow-y:scroll;height: 60vh;"></div>
            </div>
        </div>`;

    function runNER (input_text, onSuccess) {

        that.cleanResultList();
        $(result_text_element).html(spinner_html);

        let post_data = { "text" : input_text };

        $.ajax({
                url:  ner_url,
                data: JSON.stringify(post_data),
                type: 'POST',
                contentType: "application/json",
                success:
                    function(result) {
                        ner_result = result;
                        onSuccess(result);
                    },
                error:
                    function(error) {
                        console.log(error);
                        $(result_text_element).html("Failed.");
                    }
            }
        );
    }

    function parseNER (input, onSuccess) {

        let post_data = input;

        $.ajax({
                url:  parse_url,
                data: JSON.stringify(post_data),
                type: 'POST',
                contentType: "application/json",
                success:
                    function(result) {
                        ner_parsed = result;
                        onSuccess(result);
                    },
                error:
                    function(error) {
                        $(result_entities_element).html("Failed.");
                        console.log(error);
                    },
                timeout: 360000
            }
        );
    }

    let ned_request_counter = 0;
    let ned_requested = { };

    function runNED (input, onSuccess) {

        if (ner_parsed == null) {
            $(result_entities_element).html("NER data missing.");
            console.log('Parsed NER data missing.');
            return;
        }

        let keys = Object.keys(input);

        if (keys in ned_requested) return;

        ned_requested[keys] = true;
        ned_request_counter++;

        let post_data = input;

        (function(current_counter) {
            $.ajax(
                {
                    url:  ned_url,
                    data: JSON.stringify(post_data),
                    type: 'POST',
                    contentType: "application/json",
                    success:
                        function(result) {
                            Object.assign(ned_result, result);

                            if (current_counter < ned_request_counter) return;

                            onSuccess(result);
                        },
                    error:
                        function(error) {
                            console.log(error);
                        },
                    timeout: 360000
                }
            );
        })(ned_request_counter);
    }

    function selectEntity(entity, onSuccess) {

        if (entity in ned_result) {
            if ('ranking' in ned_result[entity]) {
                that.makeResultList(entity, ned_result[entity]['ranking']);
                onSuccess();
                return;
            }
            else {
                that.resultNotFound(entity);
                onSuccess();
            }
        }

        if (ned_url == null) {
            that.resultNotFound(entity);
            onSuccess();
            return;
        }

        $(result_entities_element).html(spinner_html);

        console.log(entity);

        if((ner_parsed==null) || (!(entity in ner_parsed) )){
            console.log("NER data missing: ", entity)
            $(result_entities_element).html("NER data missing.");
            return;
        }

        var input = {};
        input[entity] = ner_parsed[entity];

        runNED(input,
            function() {
                if (entity in ned_result) {
                    if ('ranking' in ned_result[entity]) {
                        that.makeResultList(entity, ned_result[entity]['ranking']);

                        onSuccess();
                    }
                    else {
                        that.resultNotFound(entity);
                        onSuccess();
                    }
                }
                else {
                    that.resultNotFound(entity);
                    onSuccess();
                }
            }
        );
    }

    function getBorderColor(entity_text, entity_type) {

        var entity = entity_text + "-" + entity_type;

        if ((entity in ned_result) && ('ranking' in ned_result[entity])) {
            var entities = ned_result[entity]['ranking'];

            var probas=[];

            entities.forEach(function(candidate) { probas.push(Number(candidate[1]["proba_1"])); });

            var max_proba = Math.max.apply(Math, probas);

            if (max_proba < 0.15)
                return "padding: 2px;border-style:dotted;border-width: thin;border-radius: 20px;border-color: gray";

            if (max_proba > 0.5)
                return "padding: 2px;border-style:solid;border-width: 2px;border-radius: 20px;border-color: gray";

            return "padding: 2px;border-style:solid;border-width: thin;border-radius: 20px;border-color: gray";
        }
        else {
            return "padding: 2px;border-style:dotted;border-width: thin;border-radius: 20px;border-color: gray";
        }
    }

    function make_surface_selector(entity_text, entity_type) {
        var entity_id = entity_text + '-' + entity_type.slice(entity_type.length-3);

        return entity_id.replace(/[^\w\s]|_/g, "-").replace(/\s+/g, "-");
    }

    function make_selectors(entity_text, entity_type) {
        var entity_id = entity_text + '-' + entity_type.slice(entity_type.length-3);

        var selector = make_surface_selector(entity_text, entity_type);

        if (entity_id in ned_result) {
            var ranking = ned_result[entity_id]['ranking'];

            ranking.forEach(
                function(item, index) {
                    selector += " " + item[1]['wikidata']
                }
            );
        }

        return selector;
    }

    function setup_el_search() {

        var pos = -1;
        var search_id=null;

        function next_occurrence(val, direction=1) {
        
            if ((val==null) || (val == "")) {
                 pos=-1;
                 search_id = "";
                 return;
            }

            var selection = $("." + val);

            if(selection.length < 1) {
                pos=-1
                search_id = "";
                return;
            }

            var elem=null;
            if ((pos==-1) || (search_id != val)){

                elem = selection.get(0);

                pos = selection.index(elem);

                //console.log(pos);

                search_id = val;
            }
            else {
                pos += direction;
                if (pos >= selection.length) pos=0;
                if (pos < 0) pos=selection.length-1;

                //console.log(pos);

                elem = selection.eq(pos).get(0);
            }

            elem.scrollIntoView();
            elem.click();
        }

        $("#search-for").on('input',
            function () {

                var val = this.value;

                next_occurrence(val);
            }
        );

        $("#entity-next").click(
            function() {
                next_occurrence(search_id, 1);
            }
        );

        $("#entity-prev").click(
            function() {
                next_occurrence(search_id, -1);
            }
        );

        var url_params = new URLSearchParams(window.location.search);

        if (url_params.has('search_id')) {
            next_occurrence(url_params.get('search_id'));

            $("#search-for").val(url_params.get('search_id'));
        }
    }

    that = {
        showNERText :
            function () {

                var text_html = [];
                var entities = [];
                var entity_types = [];

                ner_result.forEach(
                    function(sentence) {

                        var entity_text = ""
                        var entity_type = ""

                        function entity_item(selector) {
                            var item =
                                `<a id="ent-sel-${entities.length}" class="${selector} ${that.getEntityItemClass(entity_text, entity_type)}"
                                    style="${that.getColor(entity_text, entity_type)} ;${getBorderColor(entity_text, entity_type)}">
                                    ${entity_text}
                                 </a>
                                 `;

                            return item;
                        }

                        function add_entity() {

                            var selector = make_selectors(entity_text, entity_type.slice(entity_type.length-3))

                            text_html.push(entity_item(selector));

                            entities.push(entity_text);
                            entity_types.push(entity_type);
                            entity_text = "";
                        }

                        sentence.forEach(
                            function(token) {

                                 if ((entity_text != "")
                                    && ((token.prediction == 'O')
                                        || (token.prediction.startsWith('B-'))
                                        || (token.prediction.slice(-3) != entity_type))) {

                                    add_entity();
                                }

                                 if (token.prediction == 'O') {

                                    if (text_html.length > 0) text_html.push(' ');

                                    text_html.push(token.word);
                                 }
                                 else {
                                    entity_type = token.prediction.slice(-3)

                                    if (entity_text != "") entity_text += " ";

                                    entity_text += token.word;
                                 }
                            });

                         if ((entity_text != "") && (entity_text != null)) {
                            add_entity();
                         }

                         text_html.push('<br/>');
                    }
                )
                $(result_text_element).html(text_region_html);
                $("#ner-text")[0].innerHTML = text_html.join("");

                var selected_entity=null;

                entities.forEach(
                    function(entity, idx) {

                        var selector = '.' + make_surface_selector(entity, entity_types[idx]);

                        $("#ent-sel-" + idx).click(
                            function() {
                                var has_gt = $(selector).hasClass("with-gt")

                                if (selected_entity == entity + "-" + entity_types[idx]) return;
                                selected_entity = entity + "-" + entity_types[idx];

                                $(".selected").removeClass('selected');

                                selectEntity(selected_entity,
                                    function() {
                                        $(selector).addClass('selected');

                                        if (has_gt) {
                                            $(selector).addClass('with-gt');
                                        }
                                    }
                                );
                            }
                        );
                    }
                );
            },
        init:
            function(input_text) {

                if (ner_result==null) {
                    runNER( input_text,
                        function (result) {

                            ner_result = result;

                            parseNER( ner_result,
                                function(ned_result) {
                                    $(result_entities_element).html(el_html);
                                    result_entities_element="#linking-list";
                                });

                            that.showNERText();
                        }
                    );
                }
                else {
                    that.showNERText();

                    if (ned_result == null) {

                        parseNER( ner_result,
                            function(ned_result) {
                                $(result_entities_element).html(el_html);
                                result_entities_element="#linking-list";
                            });
                    }
                    else {
                        $(result_entities_element).html(el_search_html + el_html);
                        result_entities_element="#linking-list";

                        setup_el_search();
                    }
                }
            },
        makeResultList:
            function (entity, candidates) {

                function make_candidate(candidate) {

                    var parts = candidate[0].split(/(?=[\.|\-|_])/);

                    var tmp = parts.join("&shy;")

                    return `
                    <tr>
                        <td class="my-auto">
                            <a href="https://de.wikipedia.org/wiki/${candidate[0]}" target="_blank" rel="noopener noreferrer">
                                <p class="text-wrap">${tmp}</p>
                            </a>
                        </td>
                        <td class="my-auto">
                            <a href="https://www.wikidata.org/wiki/${candidate[1]['wikidata']}" target="_blank" rel="noopener noreferrer">
                                ${candidate[1]['wikidata']}
                            </a>
                        </td>
                        <td class="my-auto">
                            ${Number(candidate[1]['proba_1']).toFixed(2)}
                        </td>
                    </tr>
                    `;
                }

                var candidates_html = "";

                candidates.forEach(
                    function(candidate, index) {
                        candidates_html += make_candidate(candidate);
                    }
                );

                candidates_html =
                `
                    <table class="table">
                      <thead>
                        <tr>
                          <th scope="col">Wiki&shy;pedia</th>
                          <th scope="col">Wiki&shy;data</th>
                          <th scope="col">Confi&shy;dence</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${candidates_html}
                      </tbody>
                    </table>
                `;

                $(result_entities_element).html(candidates_html);
            },
        resultNotFound :
            function(entity) {
                $(result_entities_element).html("Not found.");
            },
        getResultEntitiesElement:
            function() {
                return result_entities_element;
            },
        cleanResultList:
            function() {
                $(result_entities_element).html("");
            },
        getColor:
            function (entity_text, entity_type) {
                if (entity_type.endsWith('PER'))
                    return "color: red"
                else if (entity_type.endsWith('LOC'))
                    return "color: green"
                else if (entity_type.endsWith('ORG'))
                    return "color: blue"
            },
        getEntityItemClass:
            function(entity_text, entity_type ) {
                return "";
            },
        setTitle:
            function(title) {
                $("#page-title").html(title);
            }
    };

    return that;
}
