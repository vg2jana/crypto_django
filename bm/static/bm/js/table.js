$(document).ready( function () {
    $('#customers.colored-due td:contains("Paid")').css("color", "green");
    $('#customers.colored-due td:contains("Not Paid")').css("color", "red");
} );