import { hasCookie } from 'cookies-next';

function UseLoginStatus() {
    var isLoggedIn = false;

    if (hasCookie('token')) {
        isLoggedIn = true;
    } else {
        isLoggedIn = false;
    }

    return isLoggedIn;
}

export { UseLoginStatus };
