
function NED(ner_url, parse_url, ned_url,
            result_text_element="#result-text", result_entities_element="#result-entities",
            ner_result=null, ned_result={}) {

    var that = null;
    var ner_parsed = null;

    var spinner_html =
            `<div class="d-flex justify-content-center">
                <div class="spinner-border align-center" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
             </div>`;

    var el_html =
         `<div class="card">
            <div class="card-header">
                <p> <b> Entity-Linking: </b> </p>
                <p style="padding: 2px;border-style:dotted;border-width: thin;border-radius: 20px;border-color: gray">EL not availabe</p>
                <p style="padding: 2px;border-style:solid;border-width: thin;border-radius: 20px;border-color: gray">EL confidence low</p>
                <p style="padding: 2px;border-style:solid;border-width: 2px;border-radius: 20px;border-color: gray">EL confidence medium</p>
            </div>
            <div class="card-body" id="linking-list">
            </div>
        </div>`;

    function runNER (input_text, onSuccess) {

        $(result_entities_element).html("");
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

                        console.log(result);
                    },
                error:
                    function(error) {
                        console.log(error);
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

    function makeResultList(entities) {
        var entities_html = "";

        entities.forEach(
            function(candidate, index) {

                if (index > 10) return;

                //if (Number(candidate[1]) < 0.1) return;

                entities_html +=
                    `<a href="https://de.wikipedia.org/wiki/${candidate[0]}" target="_blank" rel="noopener noreferrer">
                        ${candidate[0]}
                    </a>
                    (${Number(candidate[1]['proba_1']).toFixed(2)}
                    <a href="https://www.wikidata.org/wiki/${candidate[1]['wikidata']}" target="_blank" rel="noopener noreferrer">
                        ${candidate[1]['wikidata']}
                    </a>)
                    <br/>
                    `;
            }
        );

        $(result_entities_element).html(entities_html);
    }

    function selectEntity(entity, onSuccess) {

        if (entity in ned_result) {
            if ('ranking' in ned_result[entity]) {
                makeResultList(ned_result[entity]['ranking']);
                onSuccess();
                return;
            }
            else {
                $(result_entities_element).html("NOT FOUND");
            }
        }

        if (ned_url == null) {
            $(result_entities_element).html("NOT FOUND");
            return;
        }

        $(result_entities_element).html(spinner_html);

        console.log(entity);

        if((ner_parsed==null) || (!(entity in ner_parsed) )){
            console.log(entity)
            $(result_entities_element).html("NO NER DATA.");
            return;
        }

        var input = {};
        input[entity] = ner_parsed[entity];

        runNED(input,
            function() {
                if (entity in ned_result) {
                    if ('ranking' in ned_result[entity]) {
                        makeResultList(ned_result[entity]['ranking']);

                        onSuccess();
                    }
                    else {
                        $(result_entities_element).html("NOT FOUND");
                    }
                }
                else {
                    $(result_entities_element).html("NOT FOUND");
                }
            }
        );
    }

    function showNERText( data ) {

        function getColor(entity_type) {
            if (entity_type.endsWith('PER'))
                return "color: red"
            else if (entity_type.endsWith('LOC'))
                return "color: green"
            else if (entity_type.endsWith('ORG'))
                return "color: blue"
        }

        function getBorderColor(entity_text, entity_type) {

            var entity = entity_text + "-" + entity_type;

            if ((entity in ned_result) && ('ranking' in ned_result[entity])) {
                var entities = ned_result[entity]['ranking'];

                var probas=[];

                entities.forEach(function(candidate) { probas.push(Number(candidate[1]["proba_1"])); });

                var max_proba = Math.max.apply(Math, probas);

                console.log(max_proba);

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

        var text_region_html =
            `<div class="card">
                <div class="card-header">
                    Ergebnis:
                </div>
                <div class="card-block">
                    <div id="ner-text" style="overflow-y:scroll;height: 45vh;"></div>
                </div>
            </div>`;

        var text_html = [];
        var entities = [];
        var entity_types = [];

        data.forEach(
            function(sentence) {

                var entity_text = ""
                var entity_type = ""

                function entity_item(selector) {
                    var item =
                        `<a id="ent-sel-${entities.length}" class="${selector}"
                            style="${getColor(entity_type)} ;${getBorderColor(entity_text, entity_type)}">
                            ${entity_text}
                         </a>
                         `;

                    return item;
                }

                function add_entity() {
                    var selector = entity_text + ' ' + entity_type.slice(entity_type.length-3);

                    selector = selector.replace(/[^\w\s]|_/g, "").replace(/\s+/g, "-");

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

        entities.forEach(
            function(entity, idx) {
                var selector = entity + ' ' + entity_types[idx];

                selector = '.' + selector.replace(/[^\w\s]|_/g, "").replace(/\s+/g, "-");

                $("#ent-sel-" + idx).click(
                    function() {
                        $(".selected").removeClass('selected');

                        selectEntity(entity + "-" + entity_types[idx],
                            function() {
                                $(selector).addClass('selected');
                            }
                        );
                    }
                );
            }
        );
    }

    that = {
        init:
            function(input_text) {

                if (ner_result==null) {
                    runNER( input_text,
                        function (ner_result) {

                            parseNER( ner_result,
                                function(ned_result) {
                                    $(result_entities_element).html(el_html);
                                    result_entities_element="#linking-list";
                                });

                            showNERText(ner_result);
                        }
                    );
                }
                else {
                    parseNER( ner_result,
                        function(ned_result) {
                            $(result_entities_element).html(el_html);
                            result_entities_element="#linking-list";
                        });

                    showNERText(ner_result);
                }
            }
    };

    return that;
}
