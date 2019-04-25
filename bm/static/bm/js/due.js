function populate_due_modal(due_id) {
    document.getElementsByClassName('due-form-premium').id = due_id;
    $.ajax({
        type: 'GET',
        url: '/lic/due_json/' + due_id,
        data: $(this).serialize(),
        dataType: 'json',
        success: function (data) {
            document.getElementById('staticName').value = data['name'];
            document.getElementById('staticEmail').value = data['email'];
            document.getElementById('staticMobile').value = data['mobile'];
            document.getElementById('staticPolicy').value = data['policy'];
            if (data['paid'] === 'Paid') {
                document.getElementById('premiumPaid').checked = true;
            } else {
                document.getElementById('premiumUnPaid').checked = true;
            }
        }
    });
}

$(document).ready( function () {
    // Color Premium paid column
    var elements = document.getElementsByClassName('premium_paid');
    for(var i = 0; i < elements.length; i++)
    {
        element = elements.item(i);
        if (element.innerText === 'False') {
            element.innerHTML = '<a href="" data-toggle="modal" data-target="#duemodal" class="btn btn-danger btn-sm">' +
                '<span class="pencil-icon" aria-hidden="true"></span> Not Paid' +
                '</a>';
        } else {
            element.innerHTML = '<a href="" data-toggle="modal" data-target="#duemodal" class="btn btn-success btn-sm">' +
                '<span class="pencil-icon" aria-hidden="true"></span> Paid' +
                '</a>';
        }
    }

    // Due modal
    $('#duemodal').on('show.bs.modal', function() {

    });

    // On click event for due edit button
    $(document).on("click", ".premium_paid", function () {
        var due_id = $(this).attr('id');
        populate_due_modal(due_id);
    });

    // Submit Due edit
    $(".due-form").on("click", "#due-submit", function(e) {
        e.preventDefault();
        $.ajax({
            type: "POST",
            url: "/lic/due_submit/" + document.getElementsByClassName('due-form-premium').id,
            data: $('form.due-form').serialize(),
            success: function(response) {
                $("#duemodal").modal('hide');
                window.location.href = window.location.href;
            },
            error: function() {
                alert('Error');
            }
        });
        return false;
    });
} );