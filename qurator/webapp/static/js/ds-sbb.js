(function() {

var tools = null;
var has_results = false;

$(document).ready(

    function() {

        $('#nerform').submit(
            function(e){
                e.preventDefault();

                update();
            }
        );

        function main_setup(data) {
            var tmp="";

             $.each(data,
                 function(index, item){

                     selected=""
                     if (item.default) {
                         selected = "selected"
                     }

                     tmp += '<option value="' + item.id + '" ' + selected + ' >' + item.name + '</option>'
                 });
              $('#model').html(tmp);

              var url_params = new URLSearchParams(window.location.search);

              var do_update=false;

              if (url_params.has('ppn')) {

                  var ppn = url_params.get('ppn')

                  $('#ppn').val(ppn);

                  do_update = true;
              }

              if (url_params.has('model_id')) {

                  var model_id = url_params.get('model_id')

                  $('#model').val(model_id);

                  do_update = true;
              }

              if (url_params.has('el_model_id')) {

                  var el_model_id = url_params.get('el_model_id')

                  $('#el-model').val(el_model_id);

                  do_update = true;
              }

              if (url_params.has('task')) {

                  var task = url_params.get('task')

                  $('#task').val(task);

                  do_update = true;
              }

              tools = sbb_tools();

              if (do_update) update();
        }

        $.get( "ner/models")
            .done(
                function( data ) {
                    main_setup(data);
                }
                )
            .fail(
                function() {
                    main_setup([]);
                }
                );

        $.get( "ppnexamples")
            .done(
                function( data ) {
                    var tmp="";
                    $.each(data,
                        function(index, item){

                            tmp += '<option value="' + item.ppn + '">' + item.name + '</option>'
                        });
                    $('#ppnexamples').html(tmp);
                });
    });


function update() {

    if (has_results) {
        if (tools.hasUser()) $(".inp").prop("disabled", false);

        $(".inp_anonym").prop("disabled", false);
        $("#go-button").text("Go");
        has_results = false;
        tools.reset_view();

         $("#page-title").html(" <h1 >NER+EL auf den digitalisierten Sammlungen</h1>");

        return;
    }
    else {
        has_results = true;
        $(".inp").prop("disabled", true);
        $(".inp_anonym").prop("disabled", true);
        $("#go-button").text("New");
    }

    var task = $('#task').val();
    var model_id = $('#model').val();
    var el_model_id = $('#el-model').val();
    var ppn = $('#ppn').val();

    var url_params = new URLSearchParams(window.location.search);

    url_params.set('ppn', ppn)
    url_params.set('model_id', model_id)
    url_params.set('el_model_id', el_model_id)
    url_params.set('task', task)

    window.history.replaceState({}, '', `${location.pathname}?${url_params}`);

    tools.init(task,  ppn);
}

})();
