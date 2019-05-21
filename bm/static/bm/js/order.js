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
    $('#orders.colored-status').css("color", "green");
    $('#orders.colored-status td:contains("Canceled")').css("color", "orange");
} );