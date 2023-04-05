import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faStar } from '@fortawesome/free-solid-svg-icons';
import { faStar as farStar } from '@fortawesome/free-regular-svg-icons';

interface Review {
    _id: string;
    user_id: string;
    business_id: string;
    user_name?: string;
    business_name?: string;
    business_city?: string;
    stars: number;
    text: string;
    date: string;
}

interface ReviewCardProps {
    review: Review;
    isUser: boolean;
}

export default function ReviewCard({ review, isUser }: ReviewCardProps) {
    const stars = Array.from({ length: review.stars }, (_, i) => (
        <FontAwesomeIcon key={i} icon={faStar} className="text-yellow-300" />
    ));
    const emptyStars = Array.from({ length: 5 - review.stars }, (_, i) => (
        <FontAwesomeIcon key={i} icon={farStar} className="text-yellow-300" />
    ));

    return (
        <div className="p-4 my-2 bg-white shadow-md rounded-lg">
            <div className="flex items-center justify-between">
                <div className="w-4/5">
                    <h3 className="text-lg text-justify font-medium">
                        {review.text}
                    </h3>
                </div>
                <p className="text-lg font-medium text-yellow-500">
                    {stars}
                    {emptyStars}
                </p>
            </div>
            {isUser ? (
                <p className="mt-2 text-end text-lg text-gray-800">
                    {review.business_name}, {review.business_city}
                </p>
            ) : (
                <p className="mt-2 text-end text-lg text-gray-800">
                    {review.user_name}
                </p>
            )}

            <p className="mt-2 text-end text-sm text-gray-500">{review.date}</p>
        </div>
    );
}
